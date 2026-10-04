import MLX

/// Run the recurrence with the Metal kernel (true) or the step-by-step ops
/// reference (false). The ops path is slower but easy to read and check.
nonisolated(unsafe) public var gatedDeltaUseKernel = true

/// One step of the gated delta rule for every head at once.
///
///     S = g * S                      decay the memory
///     S = S + k * beta * (v - S k)   write v at key k, correcting what was there
///     y = S q                        read the memory with the query
///
/// Shapes: q, k `[B, H, Dk]`, v `[B, H, Dv]`, g and beta `[B, H]`,
/// state `[B, H, Dv, Dk]` in float32.
let gatedDeltaStep = compile(shapeless: true) { (args: [MLXArray]) -> [MLXArray] in
    let (q, k, v, g, beta) = (args[0], args[1], args[2], args[3], args[4])
    var state = args[5] * g[.ellipsis, .newAxis, .newAxis]
    let kvMemory = (state * k[.ellipsis, .newAxis, 0...]).sum(axis: -1)
    let delta = (v - kvMemory) * beta[.ellipsis, .newAxis]
    state = state + k[.ellipsis, .newAxis, 0...] * delta[.ellipsis, .newAxis]
    let y = (state * q[.ellipsis, .newAxis, 0...]).sum(axis: -1)
    return [y.asType(q.dtype), state]
}

/// Runs the recurrence over `T` tokens with plain MLX ops, one step at a
/// time. Returns outputs `[B, T, Hv, Dv]`, the final state, and the state
/// after every token (used to roll back rejected speculative tokens).
func gatedDeltaOps(
    q: MLXArray, k: MLXArray, v: MLXArray, g: MLXArray, beta: MLXArray, state: MLXArray
) -> (MLXArray, MLXArray, [MLXArray]) {
    let T = q.dim(1)
    var state = state
    var ys = [MLXArray]()
    var states = [MLXArray]()
    for t in 0 ..< T {
        let r = gatedDeltaStep([q[0..., t], k[0..., t], v[0..., t], g[0..., t], beta[0..., t], state])
        ys.append(r[0])
        state = r[1]
        states.append(state)
    }
    return (stacked(ys, axis: 1), state, states)
}

/// The same recurrence as a Metal kernel. Each SIMD group owns one row of
/// one head's state and keeps it in registers for all `T` tokens, so the
/// state is read from and written to memory once per call, not once per token.
private let gatedDeltaKernel = MLXFast.metalKernel(
    name: "gated_delta_step",
    inputNames: ["q", "k", "v", "g", "beta", "state_in", "T"],
    outputNames: ["y", "state_out", "history"],
    source: """
        auto n = thread_position_in_grid.z;
        auto b_idx = n / Hv;
        auto h_idx = n % Hv;
        constexpr int n_per_t = Dk / 32;

        auto q_ = q + b_idx * T * Hv * Dk + h_idx * Dk;
        auto k_ = k + b_idx * T * Hv * Dk + h_idx * Dk;
        auto v_ = v + b_idx * T * Hv * Dv + h_idx * Dv;
        y += b_idx * T * Hv * Dv + h_idx * Dv;

        auto dk_idx = thread_position_in_threadgroup.x;
        auto dv_idx = thread_position_in_grid.y;

        auto i_state = state_in + (n * Dv + dv_idx) * Dk;
        auto o_state = state_out + (n * Dv + dv_idx) * Dk;

        float state[n_per_t];
        for (int i = 0; i < n_per_t; ++i) {
          state[i] = static_cast<float>(i_state[n_per_t * dk_idx + i]);
        }

        auto g_ = g + b_idx * T * Hv;
        auto beta_ = beta + b_idx * T * Hv;

        for (int t = 0; t < T; ++t) {
          float kv_mem = 0.0f;
          for (int i = 0; i < n_per_t; ++i) {
            auto s_idx = n_per_t * dk_idx + i;
            state[i] = state[i] * g_[h_idx];
            kv_mem += state[i] * k_[s_idx];
          }
          kv_mem = simd_sum(kv_mem);

          auto delta = (v_[dv_idx] - kv_mem) * beta_[h_idx];

          float out = 0.0f;
          for (int i = 0; i < n_per_t; ++i) {
            auto s_idx = n_per_t * dk_idx + i;
            state[i] = state[i] + k_[s_idx] * delta;
            out += state[i] * q_[s_idx];
          }
          out = simd_sum(out);
          if (thread_index_in_simdgroup == 0) {
            y[dv_idx] = static_cast<InT>(out);
          }
          q_ += Hv * Dk;
          k_ += Hv * Dk;
          v_ += Hv * Dv;
          if (SaveHistory) {
            // history: [T, B * Hv, Dv, Dk], the state after token t.
            auto h_state = history + ((t * B * Hv + n) * Dv + dv_idx) * Dk;
            for (int i = 0; i < n_per_t; ++i) {
              h_state[n_per_t * dk_idx + i] = static_cast<StT>(state[i]);
            }
          }
          y += Hv * Dv;
          g_ += Hv;
          beta_ += Hv;
        }
        for (int i = 0; i < n_per_t; ++i) {
          o_state[n_per_t * dk_idx + i] = static_cast<StT>(state[i]);
        }
        """
)

/// Returns outputs `[B, T, Hv, Dv]`, the final state, and, when
/// `saveHistory` is set, the state after every token `[T, B, Hv, Dv, Dk]`.
func gatedDeltaMetal(
    q: MLXArray, k: MLXArray, v: MLXArray, g: MLXArray, beta: MLXArray, state: MLXArray,
    saveHistory: Bool = false
) -> (MLXArray, MLXArray, MLXArray?) {
    let (B, T, H, Dk) = (q.dim(0), q.dim(1), q.dim(2), q.dim(3))
    let Dv = v.dim(3)
    let out = gatedDeltaKernel(
        [q, k, v, g, beta, state, T],
        template: [("InT", q.dtype), ("StT", state.dtype), ("Dk", Dk), ("Dv", Dv), ("Hv", H),
                   ("B", B), ("SaveHistory", saveHistory)],
        grid: (32, Dv, B * H),
        threadGroup: (32, 4, 1),
        outputShapes: [[B, T, H, Dv], state.shape, saveHistory ? [T] + state.shape : [1]],
        outputDTypes: [q.dtype, state.dtype, state.dtype])
    return (out[0], out[1], saveHistory ? out[2] : nil)
}

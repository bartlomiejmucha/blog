import Foundation
import os

/// Counters exposed at /metrics in the Prometheus text format.
final class Metrics: Sendable {
    struct Values {
        var requests = 0
        var rejected = 0
        var cancelled = 0
        var promptTokens = 0
        var cachedPromptTokens = 0
        var completionTokens = 0
        var timeToFirstTokenSum = 0.0
        var timeToFirstTokenCount = 0
        var decodeSecondsSum = 0.0
        var inFlight = 0
    }

    private let values = OSAllocatedUnfairLock(initialState: Values())

    func update(_ body: @Sendable (inout Values) -> Void) {
        values.withLock { body(&$0) }
    }

    func render() -> String {
        let v = values.withLock { $0 }
        return """
            # TYPE qwenserve_requests_total counter
            qwenserve_requests_total \(v.requests)
            # TYPE qwenserve_rejected_total counter
            qwenserve_rejected_total \(v.rejected)
            # TYPE qwenserve_cancelled_total counter
            qwenserve_cancelled_total \(v.cancelled)
            # TYPE qwenserve_prompt_tokens_total counter
            qwenserve_prompt_tokens_total \(v.promptTokens)
            # TYPE qwenserve_cached_prompt_tokens_total counter
            qwenserve_cached_prompt_tokens_total \(v.cachedPromptTokens)
            # TYPE qwenserve_completion_tokens_total counter
            qwenserve_completion_tokens_total \(v.completionTokens)
            # TYPE qwenserve_time_to_first_token_seconds summary
            qwenserve_time_to_first_token_seconds_sum \(v.timeToFirstTokenSum)
            qwenserve_time_to_first_token_seconds_count \(v.timeToFirstTokenCount)
            # TYPE qwenserve_decode_seconds_total counter
            qwenserve_decode_seconds_total \(v.decodeSecondsSum)
            # TYPE qwenserve_in_flight gauge
            qwenserve_in_flight \(v.inFlight)

            """
    }
}

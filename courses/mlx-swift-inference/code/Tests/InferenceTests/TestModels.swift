import Foundation

/// Local model directories. Tests that need weights are skipped when these
/// are missing. Override with QWEN3_DIR / QWEN35_DIR.
enum TestModels {
    static func directory(env: String, repo: String) -> URL? {
        if let path = ProcessInfo.processInfo.environment[env] { return URL(filePath: path) }
        let snapshots = FileManager.default.homeDirectoryForCurrentUser
            .appending(path: ".cache/huggingface/hub/models--\(repo.replacingOccurrences(of: "/", with: "--"))/snapshots")
        guard let first = try? FileManager.default.contentsOfDirectory(at: snapshots, includingPropertiesForKeys: nil).first
        else { return nil }
        return first
    }

    static var qwen3: URL? { directory(env: "QWEN3_DIR", repo: "mlx-community/Qwen3-0.6B-4bit") }
    static var qwen35: URL? { directory(env: "QWEN35_DIR", repo: "Qwen/Qwen3.5-0.8B") }
}

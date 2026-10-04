// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "QwenServe",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "Inference", targets: ["Inference"]),
        .executable(name: "infer", targets: ["infer"]),
        .executable(name: "serve", targets: ["serve"]),
        .executable(name: "mlx-basics", targets: ["mlx-basics"]),
    ],
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift", exact: "0.32.3"),
        .package(url: "https://github.com/huggingface/swift-transformers", exact: "1.3.4"),
        .package(url: "https://github.com/hummingbird-project/hummingbird", exact: "2.27.0"),
    ],
    targets: [
        .target(
            name: "Inference",
            dependencies: [
                .product(name: "MLX", package: "mlx-swift"),
                .product(name: "MLXNN", package: "mlx-swift"),
                .product(name: "MLXFast", package: "mlx-swift"),
                .product(name: "Tokenizers", package: "swift-transformers"),
            ]
        ),
        .executableTarget(
            name: "infer",
            dependencies: ["Inference"]
        ),
        .executableTarget(
            name: "mlx-basics",
            dependencies: [
                .product(name: "MLX", package: "mlx-swift"),
                .product(name: "MLXNN", package: "mlx-swift"),
            ]
        ),
        .testTarget(
            name: "InferenceTests",
            dependencies: ["Inference"]
        ),
        .executableTarget(
            name: "serve",
            dependencies: [
                "Inference",
                .product(name: "Hummingbird", package: "hummingbird"),
            ]
        ),
    ]
)

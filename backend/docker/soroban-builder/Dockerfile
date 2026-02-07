# Soroban Contract Builder Image
# Uses pre-built soroban-cli binary to avoid memory-intensive compilation

FROM rust:1.85-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install wasm32 target
RUN rustup target add wasm32-unknown-unknown

# CRITICAL: Disable WebAssembly reference-types feature
# Rust 1.85+ enables reference-types by default, but Soroban VM doesn't support it
# This causes "reference-types not enabled: zero byte expected" errors on deployment
ENV RUSTFLAGS="-C target-feature=-reference-types"

# Download pre-built soroban-cli binary from Stellar releases
# Detect architecture and download appropriate binary
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        STELLAR_ARCH="x86_64-unknown-linux-gnu"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        STELLAR_ARCH="aarch64-unknown-linux-gnu"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl -L -o /tmp/soroban.tar.gz \
        "https://github.com/stellar/stellar-cli/releases/download/v21.0.0/soroban-cli-21.0.0-${STELLAR_ARCH}.tar.gz" && \
    tar -xzf /tmp/soroban.tar.gz -C /usr/local/bin && \
    rm /tmp/soroban.tar.gz && \
    chmod +x /usr/local/bin/soroban

# Verify installation
RUN soroban --version

# Pre-warm cargo cache by building a minimal contract
# This compiles all 161+ Soroban dependencies into the image
COPY warmup /warmup
WORKDIR /warmup
RUN soroban contract build && rm -rf /warmup target

# Create workspace directory
WORKDIR /workspace

# Default command - build the contract
CMD ["soroban", "contract", "build"]

"""
Docker Compilation Service

Compiles Soroban (Rust) smart contracts in isolated Docker containers.
Handles:
- Ephemeral container creation
- Code mounting
- Compilation with timeout
- WASM extraction
- Cleanup
"""

import asyncio
import os
import shutil
import uuid
from typing import TypedDict
from pathlib import Path

import docker
from docker.errors import ContainerError, ImageNotFound, APIError

from app.core.config import settings


# Directory for contract builds - must be accessible from host for Docker volume mounting
# When running in Docker, /app is mounted from ./backend on host
BUILD_DIR = Path(os.environ.get("BUILD_DIR", "/app/builds"))


def get_host_build_path(build_id: str) -> str:
    """
    Get the host path for a build directory.

    When running inside Docker, we need to translate the container path
    to a host path that Docker can mount into the builder container.
    """
    host_build_dir = os.environ.get("HOST_BUILD_DIR")

    if host_build_dir:
        # Use explicitly configured host path
        return f"{host_build_dir}/{build_id}"

    # Fallback: assume we're running outside Docker or builds dir is at ./builds
    # relative to where Docker is run from
    return str(BUILD_DIR / build_id)


class CompilationResult(TypedDict):
    success: bool
    wasm: bytes | None
    logs: list[str]
    error: str | None


# Soroban builder image name
BUILDER_IMAGE = "halo-soroban-builder:latest"

# Fallback to official Stellar image if custom not built
FALLBACK_IMAGE = "stellar/quickstart:soroban-dev"

# Persistent cargo cache volume for faster builds
CARGO_CACHE_VOLUME = "halo-cargo-cache"


async def compile_contract(
    lib_rs: str,
    cargo_toml: str,
    timeout_seconds: int = None,
) -> CompilationResult:
    """
    Compile a Soroban smart contract to WASM.

    Args:
        lib_rs: Content of lib.rs file
        cargo_toml: Content of Cargo.toml file
        timeout_seconds: Maximum compilation time (default from settings)

    Returns:
        CompilationResult with success status, WASM bytes, logs, and any errors
    """

    timeout = timeout_seconds or settings.docker_timeout_seconds
    logs = []

    # Create build directory with unique ID
    # We use BUILD_DIR which is mounted from host, so Docker can access it
    build_id = str(uuid.uuid4())[:8]
    build_path = BUILD_DIR / build_id
    host_build_path = get_host_build_path(build_id)

    try:
        # Ensure builds directory exists
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        build_path.mkdir(parents=True, exist_ok=True)

        # Create project structure
        src_dir = build_path / "src"
        src_dir.mkdir()

        # Write files
        (src_dir / "lib.rs").write_text(lib_rs)
        (build_path / "Cargo.toml").write_text(cargo_toml)

        logs.append("Contract files prepared")

        try:
            # Run compilation in Docker
            # Pass the host path for volume mounting
            result = await run_docker_build(
                source_dir=str(build_path),
                host_source_dir=host_build_path,
                timeout=timeout,
                logs=logs,
            )

            return result

        except asyncio.TimeoutError:
            logs.append(f"Compilation timed out after {timeout} seconds")
            return CompilationResult(
                success=False,
                wasm=None,
                logs=logs,
                error=f"Compilation timed out after {timeout} seconds"
            )
        except Exception as e:
            logs.append(f"Compilation error: {str(e)}")
            return CompilationResult(
                success=False,
                wasm=None,
                logs=logs,
                error=str(e)
            )
    finally:
        # Clean up build directory
        try:
            if build_path.exists():
                shutil.rmtree(build_path)
        except Exception:
            pass  # Ignore cleanup errors


async def run_docker_build(
    source_dir: str,
    host_source_dir: str,
    timeout: int,
    logs: list[str],
) -> CompilationResult:
    """
    Run the Docker container for compilation.

    Uses asyncio to run in executor to not block.

    Args:
        source_dir: Path to source inside the backend container (for reading results)
        host_source_dir: Path on the Docker host (for volume mounting)
    """

    loop = asyncio.get_event_loop()

    return await asyncio.wait_for(
        loop.run_in_executor(
            None,
            _sync_docker_build,
            source_dir,
            host_source_dir,
            logs,
        ),
        timeout=timeout
    )


def _sync_docker_build(
    source_dir: str,
    host_source_dir: str,
    logs: list[str],
) -> CompilationResult:
    """
    Synchronous Docker build (runs in executor).

    Args:
        source_dir: Path to source inside the backend container (for reading results)
        host_source_dir: Path on the Docker host (for volume mounting)
    """

    client = docker.from_env()
    container = None

    try:
        # Check if our custom image exists, fall back to official
        try:
            client.images.get(BUILDER_IMAGE)
            image = BUILDER_IMAGE
            logs.append(f"Using custom builder image: {BUILDER_IMAGE}")
        except ImageNotFound:
            # Fallback to standard Rust image (must support edition2024)
            image = "rust:1.82-slim"
            logs.append(f"Using fallback image: {image}")

        logs.append("Starting compilation container...")

        # Build command
        # CRITICAL: Set RUSTFLAGS to disable reference-types
        # Rust 1.85+ enables WebAssembly reference-types by default, but Soroban VM doesn't support it
        # This causes "reference-types not enabled: zero byte expected" errors on deployment
        build_cmd = """
        set -e
        cd /workspace
        
        # Disable WebAssembly reference-types (not supported by Soroban VM)
        export RUSTFLAGS="-C target-feature=-reference-types"

        # Debug: list files
        echo "Files in /workspace:"
        ls -la /workspace/
        ls -la /workspace/src/ 2>/dev/null || echo "No src directory"

        # Install wasm target if not present
        rustup target add wasm32-unknown-unknown 2>/dev/null || true

        # Install soroban-cli if not present
        which soroban || cargo install --locked soroban-cli --version 21.0.0

        # Build the contract
        echo "Building contract with RUSTFLAGS: $RUSTFLAGS"
        soroban contract build

        # Find and copy the wasm file
        find target -name "*.wasm" -type f | head -1 | xargs -I {} cp {} /workspace/output.wasm

        echo "Build complete!"
        """

        # Run container - use host_source_dir for volume mounting
        # This is the path on the Docker host, not inside the backend container
        # Also mount persistent cargo cache volume for faster builds
        container = client.containers.run(
            image=image,
            command=["bash", "-c", build_cmd],
            volumes={
                host_source_dir: {"bind": "/workspace", "mode": "rw"},
                CARGO_CACHE_VOLUME: {"bind": "/root/.cargo", "mode": "rw"},
            },
            working_dir="/workspace",
            detach=True,
            remove=False,  # We'll remove manually after getting logs
            mem_limit="2g",
            network_disabled=False,  # Need network for cargo
        )
        
        logs.append("Container started, compiling...")
        
        # Wait for completion and get logs
        result = container.wait(timeout=settings.docker_timeout_seconds)
        container_logs = container.logs().decode("utf-8")
        
        # Add container logs
        for line in container_logs.split("\n"):
            if line.strip():
                logs.append(line.strip())
        
        # Check exit code
        exit_code = result.get("StatusCode", 1)

        if exit_code != 0:
            # Extract the most useful error info from container logs
            # Rust compiler errors are the most helpful for the AI to fix
            error_lines = []
            for line in container_logs.split("\n"):
                stripped = line.strip()
                if stripped and any(kw in stripped.lower() for kw in [
                    "error", "cannot find", "expected", "mismatched",
                    "not found", "no method", "unused", "unresolved",
                    "aborting", "help:", "note:", "warning:",
                    "macro", "trait", "type", "-->",
                ]):
                    error_lines.append(stripped)

            # Combine: use extracted errors if available, else full log tail
            if error_lines:
                error_msg = "\n".join(error_lines[-20:])
            else:
                # Fallback: last 15 lines of output
                all_lines = [l.strip() for l in container_logs.split("\n") if l.strip()]
                error_msg = "\n".join(all_lines[-15:]) if all_lines else "Compilation failed"

            logs.append(f"Build failed with exit code {exit_code}")
            return CompilationResult(
                success=False,
                wasm=None,
                logs=logs,
                error=error_msg
            )
        
        # Read WASM file
        wasm_path = Path(source_dir) / "output.wasm"
        
        if not wasm_path.exists():
            # Try to find wasm in target directory
            target_dir = Path(source_dir) / "target" / "wasm32-unknown-unknown" / "release"
            wasm_files = list(target_dir.glob("*.wasm")) if target_dir.exists() else []
            
            if wasm_files:
                wasm_path = wasm_files[0]
            else:
                logs.append("WASM file not found after build")
                return CompilationResult(
                    success=False,
                    wasm=None,
                    logs=logs,
                    error="WASM file not found after compilation"
                )
        
        wasm_bytes = wasm_path.read_bytes()
        logs.append(f"WASM compiled successfully ({len(wasm_bytes)} bytes)")
        
        return CompilationResult(
            success=True,
            wasm=wasm_bytes,
            logs=logs,
            error=None
        )
        
    except ContainerError as e:
        logs.append(f"Container error: {e.stderr.decode() if e.stderr else str(e)}")
        return CompilationResult(
            success=False,
            wasm=None,
            logs=logs,
            error=str(e)
        )
        
    except APIError as e:
        logs.append(f"Docker API error: {str(e)}")
        return CompilationResult(
            success=False,
            wasm=None,
            logs=logs,
            error=f"Docker error: {str(e)}"
        )
        
    finally:
        # Cleanup container
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass


async def check_docker_available() -> bool:
    """Check if Docker is available and running"""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


async def build_builder_image() -> bool:
    """
    Build the custom Soroban builder image.
    
    This should be run once during setup.
    """
    try:
        client = docker.from_env()
        
        # Path to Dockerfile
        dockerfile_dir = Path(__file__).parent.parent.parent / "docker" / "soroban-builder"
        
        if not dockerfile_dir.exists():
            return False
        
        # Build image
        client.images.build(
            path=str(dockerfile_dir),
            tag=BUILDER_IMAGE,
            rm=True,
        )
        
        return True
    except Exception as e:
        print(f"Failed to build builder image: {e}")
        return False

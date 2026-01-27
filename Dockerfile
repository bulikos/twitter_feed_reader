FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Configure the environment
ENV UV_PROJECT_ENVIRONMENT=/venv
ENV UV_COMPILE_BYTECODE=1

# Use /src as the standard project root directory
WORKDIR /src

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Add virtual environment to PATH
ENV PATH="/venv/bin:$PATH"

# Run as a module from the source root
CMD ["python", "-m", "app.main"]

# Python Environment & Package Management

This project uses [UV](https://docs.astral.sh/uv/) as the package and environment manager. UV is a modern, fast Python package manager written in Rust that replaces pip, pip-tools, and virtualenv.

## Table of Contents

- [Why UV?](#why-uv)
- [Getting Started](#getting-started)
- [Managing Dependencies](#managing-dependencies)
- [Running Code](#running-code)
- [Environment Management](#environment-management)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)

---

## Why UV?

UV provides several advantages over traditional tools:

- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic installs** with lockfile (`uv.lock`)
- 📦 **All-in-one tool** - no need for pip, virtualenv, pip-tools separately
- 🎯 **Python version management** built-in
- 🔄 **Modern workflow** using `pyproject.toml` standard

---

## Getting Started

### Installation

If you don't have UV installed yet:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv

# Or via pip
pip install uv
```

### Setting Up This Project

When you clone this repository or pull new changes:

```bash
# Sync the environment (installs all dependencies from pyproject.toml)
uv sync
```

This creates a `.venv` directory and installs all dependencies listed in `pyproject.toml` and pinned in `uv.lock`.

---

## Managing Dependencies

### Adding Packages

```bash
# Add a runtime dependency
uv add package-name

# Add a specific version
uv add package-name==1.2.3

# Add with version constraints
uv add "package-name>=1.2,<2.0"

# Add a development dependency (testing, linting, etc.)
uv add --dev pytest
uv add --dev black ruff mypy
```

### Removing Packages

```bash
# Remove a dependency
uv remove package-name
```

### Updating Dependencies

```bash
# Update all dependencies to latest compatible versions
uv lock --upgrade

# Update a specific package
uv lock --upgrade-package package-name

# Then sync to apply updates
uv sync
```

### Viewing Dependencies

```bash
# List installed packages
uv pip list

# Show dependency tree
uv tree

# Show outdated packages
uv pip list --outdated
```

---

## Running Code

UV provides the `uv run` command to execute code in the project environment:

### Running Python Scripts

```bash
# Run a Python script
uv run python main.py

# Run a specific script
uv run python scripts/analyze.py
```

### Running Jupyter

```bash
# Start Jupyter Notebook
uv run jupyter notebook

# Start Jupyter Lab
uv run jupyter lab

# Run a specific notebook non-interactively
uv run jupyter nbconvert --to notebook --execute notebook.ipynb
```

### Running Tools

```bash
# Run any installed tool
uv run black .
uv run pytest
uv run mypy app/

# Start Python REPL
uv run python
uv run ipython
```

### Direct Python Execution

You can also activate the environment manually if needed:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Now you can run commands without 'uv run'
python main.py
jupyter notebook

# Deactivate when done
deactivate
```

---

## Environment Management

### Creating/Recreating Environment

```bash
# Sync environment (creates .venv if missing)
uv sync

# Force recreate the environment
rm -rf .venv
uv sync
```

### Python Version

The project Python version is specified in `pyproject.toml`:

```toml
[project]
requires-python = ">=3.13"
```

And pinned in `.python-version` file. UV automatically uses this version.

### Managing Python Versions

```bash
# Install a specific Python version
uv python install 3.13

# List available Python versions
uv python list

# Use a specific Python version for this project
uv python pin 3.13
```

---

## Common Workflows

### Starting Work on the Project

```bash
# 1. Pull latest changes
git pull

# 2. Sync dependencies (installs new deps, removes unused ones)
uv sync

# 3. Start coding!
uv run python main.py
```

### Adding a New Feature

```bash
# 1. Add any new dependencies you need
uv add requests beautifulsoup4

# 2. Write your code
# 3. Test it
uv run python my_feature.py

# 4. Commit both pyproject.toml and uv.lock
git add pyproject.toml uv.lock
git commit -m "Add new feature with requests and beautifulsoup4"
```

### Running Notebooks

```bash
# Start Jupyter Lab
uv run jupyter lab

# The kernel will automatically use the UV environment
# All packages from pyproject.toml will be available
```

### Setting Up JupyterLab Kernel

If you need the environment available as a Jupyter kernel:

```bash
# Install ipykernel (already in dependencies)
# Register the kernel
uv run python -m ipykernel install --user --name=x-sourcer --display-name="X-Sourcer"

# Now you can select "X-Sourcer" kernel in Jupyter
```

---

## Troubleshooting

### Environment Issues

**Problem**: Dependencies not found when running code

```bash
# Solution: Sync the environment
uv sync
```

**Problem**: Old packages still present after removing

```bash
# Solution: Clean and sync
rm -rf .venv
uv sync
```

### Lock File Issues

**Problem**: `uv.lock` is out of sync with `pyproject.toml`

```bash
# Solution: Regenerate the lock file
uv lock
uv sync
```

### Python Version Issues

**Problem**: Wrong Python version being used

```bash
# Check current Python version
uv run python --version

# Pin to specific version
uv python pin 3.13
uv sync
```

### Jupyter Kernel Issues

**Problem**: Packages not available in Jupyter notebook

```bash
# Make sure you're using the correct kernel
# 1. Start Jupyter from UV environment
uv run jupyter lab

# 2. Or reinstall the kernel
uv run python -m ipykernel install --user --name=x-sourcer --display-name="X-Sourcer" --force
```

---

## Project Files

### `pyproject.toml`

The main project configuration file. Contains:
- Project metadata (name, version, description)
- Python version requirements
- Runtime dependencies
- Development dependencies (if any)

**Example:**
```toml
[project]
name = "x-sourcer"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "aiohttp>=3.13.3",
    "pandas>=3.0.0",
]
```

### `uv.lock`

Lockfile that pins exact versions of all dependencies (including transitive ones). This ensures:
- **Reproducible installs** across different machines
- **Consistent environments** for all team members
- **Security** - you know exactly what versions are installed

**⚠️ Always commit this file to version control!**

### `.python-version`

Specifies the Python version for this project. UV automatically uses this version.

### `.venv/`

The virtual environment directory. Contains all installed packages.

**⚠️ Do NOT commit this to version control** (should be in `.gitignore`)

---

## Quick Reference

| Task | Command |
|------|---------|
| Install dependencies | `uv sync` |
| Add package | `uv add package-name` |
| Add dev package | `uv add --dev package-name` |
| Remove package | `uv remove package-name` |
| Update all packages | `uv lock --upgrade && uv sync` |
| Run Python script | `uv run python script.py` |
| Start Jupyter | `uv run jupyter lab` |
| List packages | `uv pip list` |
| Show dependency tree | `uv tree` |
| Clean environment | `rm -rf .venv && uv sync` |

---

## Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)

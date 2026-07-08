#!/usr/bin/env sh
# Set up an isolated Python environment for running the test suite, without
# relying on a system `python3 -m venv` (which needs the `python3-venv` /
# `ensurepip` package that our Node CI agents do not ship).
#
# Uses `uv` (https://astral.sh) — a standalone binary that manages its own
# Python and virtual environments. It requires no root, no apt, and no system
# ensurepip; if the agent lacks a suitable Python, uv downloads a managed one.
#
# For locked-down CI where astral.sh is unreachable, override either:
#   UV_BINARY=/path/to/uv        use a pre-baked uv binary directly
#   UV_INSTALL_URL=https://...   fetch the install script from a mirror
set -eu

# Pinned interpreter for the venv. uv fetches a managed CPython of this version
# when the agent does not already provide it.
PYTHON_VERSION="3.12"

# 1. Locate uv, or install it user-locally (~/.local/bin) with no root.
if [ -n "${UV_BINARY:-}" ] && [ -x "${UV_BINARY}" ]; then
  UV="${UV_BINARY}"
elif command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
else
  echo "uv not found; installing to ~/.local/bin ..."
  export UV_INSTALL_DIR="$HOME/.local/bin"
  curl -LsSf "${UV_INSTALL_URL:-https://astral.sh/uv/install.sh}" | sh
  UV="$HOME/.local/bin/uv"
fi

echo "Using $("$UV" --version) at $UV"

# 2. Create the .venv on the pinned Python (managed install if needed).
"$UV" venv --python "$PYTHON_VERSION" .venv

# 3. Install the package with its dev dependencies into .venv.
VIRTUAL_ENV="$PWD/.venv" "$UV" pip install -e ".[dev]"

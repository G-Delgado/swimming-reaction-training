#!/usr/bin/env bash
#
# Build the APK locally (WSL2 / Ubuntu / any Linux), with no dependency on
# GitHub Actions.
#
#   bash build-local.sh
#
# First run downloads the Android SDK/NDK (~5-8 GB) and takes 20-40 minutes.
# Later runs reuse that and finish in a couple of minutes.
#
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "==> Project: $PROJECT_DIR"

if [ ! -f buildozer.spec ]; then
  echo "!! buildozer.spec not found. Run this from the project folder." >&2
  exit 1
fi

# --- system packages ---------------------------------------------------
echo "==> Installing system dependencies (sudo required)"
sudo apt-get update
sudo apt-get install -y \
  git zip unzip openjdk-17-jdk python3-pip python3-venv \
  autoconf libtool pkg-config zlib1g-dev libncurses-dev \
  cmake libffi-dev libssl-dev build-essential ccache
sudo apt-get install -y libtinfo6 || true

# --- python toolchain in an isolated venv ------------------------------
# A venv keeps buildozer/cython off the system python, which is what kept
# breaking in CI when a stray newer interpreter shadowed the pinned one.
VENV="$PROJECT_DIR/.venv-build"
if [ ! -d "$VENV" ]; then
  echo "==> Creating build virtualenv"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install "buildozer" "cython==0.29.36"

echo "==> Versions"
python --version
java -version 2>&1 | head -1
buildozer --version

# --- build --------------------------------------------------------------
echo "==> Building debug APK (this is the long part)"
yes | buildozer android debug

echo ""
echo "======================================================"
if ls bin/*.apk >/dev/null 2>&1; then
  ls -lh bin/*.apk
  echo ""
  echo "APK built. From Windows you can find it at:"
  echo "  \\\\wsl\$\\Ubuntu${PROJECT_DIR}/bin/"
  echo "Copy it to your phone and open it (allow install from unknown sources)."
else
  echo "Build finished but no APK in bin/ — scroll up for the error."
  exit 1
fi
echo "======================================================"

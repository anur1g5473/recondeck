#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
for tool in dig whois; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "$tool is missing. Install it with: sudo apt update && sudo apt install -y dnsutils whois python3 python3-venv python3-pip" >&2
    exit 1
  fi
done

VENV_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/recondeck/venv"
if [ ! -x "$VENV_DIR/bin/python" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
  mkdir -p "$(dirname "$VENV_DIR")"
  if ! python3 -m venv --clear "$VENV_DIR"; then
    echo "Python virtual-environment support is missing. Install it with: sudo apt update && sudo apt install -y python3-venv python3-pip" >&2
    exit 1
  fi
fi
. "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt >/dev/null
python app.py --port 5000

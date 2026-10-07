#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt >/dev/null
if ! command -v dig >/dev/null 2>&1; then
  echo "dig is missing. Install it with: sudo apt update && sudo apt install -y dnsutils whois python3 python3-venv python3-pip"
  exit 1
fi
if ! command -v whois >/dev/null 2>&1; then
  echo "whois is missing. Install it with: sudo apt update && sudo apt install -y dnsutils whois python3 python3-venv python3-pip"
  exit 1
fi
python app.py --port 5000

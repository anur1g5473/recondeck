import os
import secrets
from pathlib import Path

APP_NAME = "RECONDECK"
TERMS_VERSION = 1
APP_TOKEN = os.environ.get("RECONDECK_TOKEN") or ""
RESOLVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
ALLOWED_COMMANDS = {"dig", "whois"}
MAX_OUTPUT_BYTES = 200 * 1024
MAX_CONCURRENT_PROCESSES = 8
PROJECT_ROOT = Path(__file__).resolve().parent.parent
START_PORT = 5000
HOST = "127.0.0.1"

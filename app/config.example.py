"""Copy to app/config.py when setting up a fresh clone."""
import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

# The only directory exposed to the read-only project tools.
PROJECT_ROOT = os.getenv("PROJECT_ROOT", str(REPO_ROOT))

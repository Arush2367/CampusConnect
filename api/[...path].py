"""Catch-all Vercel Function for existing /api/* endpoints."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vercel_handler import VercelHandler


class handler(VercelHandler):
    pass

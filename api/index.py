import sys
import pathlib

# Add backend directory to sys.path for Vercel Serverless Function runtime
backend_dir = str(pathlib.Path(__file__).resolve().parents[1] / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import create_app

app = create_app()

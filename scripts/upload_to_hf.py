"""Upload all project files to HuggingFace Space.

Usage:
    HF_TOKEN=your_token python scripts/upload_to_hf.py
    # or set HF_TOKEN in your .env
"""
import os
import pathlib
from huggingface_hub import HfApi

TOKEN = os.getenv("HF_TOKEN", "")
REPO = "vamsi-op/automated-research-assistant"

if not TOKEN:
    raise ValueError("Set HF_TOKEN environment variable")

api = HfApi(token=TOKEN)
root = pathlib.Path(__file__).parent.parent

IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "data", "logs", ".vercel", ".cache"}
IGNORE_EXT = {".pyc", ".pyo", ".log", ".bin", ".pt", ".pth", ".onnx"}

for f in root.rglob("*"):
    if not f.is_file():
        continue
    parts = set(f.relative_to(root).parts)
    if parts & IGNORE_DIRS:
        continue
    if f.suffix in IGNORE_EXT:
        continue
    if f.name.startswith(".env") and f.name != ".env.example":
        continue
    path_in_repo = str(f.relative_to(root)).replace("\\", "/")
    try:
        api.upload_file(
            path_or_fileobj=str(f),
            path_in_repo=path_in_repo,
            repo_id=REPO,
            repo_type="space",
        )
        print(f"  + {path_in_repo}")
    except Exception as e:
        print(f"  ! {path_in_repo}: {e}")

print("Upload complete")

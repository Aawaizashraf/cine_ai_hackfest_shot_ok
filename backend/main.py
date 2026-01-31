"""
Thin entrypoint: re-export app from app.main for `uvicorn main:app`.
Use `uvicorn app.main:app` for the same behavior.
"""
from app.main import app

__all__ = ["app"]

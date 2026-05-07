"""WSGI entry point. Re-exports the Flask app so deployment platforms
that expect `main:app` (Railway, Render, Fly, etc.) can find it."""

from app import app

__all__ = ['app']

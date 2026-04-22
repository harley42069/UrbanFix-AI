"""API endpoints package.

This module intentionally avoids eager imports to keep startup/tests resilient
when optional ML dependencies are not available.
"""

__all__: list[str] = []

__all__ = [
    "auth",
    "signalements",
    "detection",
    "generation",
    "estimation",
    "upload",
    "analysis",
    "reports",
    "process",
    "websocket_endpoint"
]

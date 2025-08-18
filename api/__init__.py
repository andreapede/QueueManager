"""
API package for Queue Management System
Contains REST API endpoints
"""

from .endpoints import api_bp, init_api

__all__ = [
    'api_bp',
    'init_api'
]

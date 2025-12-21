"""
SVA OAuth Client - A Django package for integrating SVA (Secure Vault Authentication) OAuth provider.

This package provides a complete solution for Django applications to authenticate users
via SVA OAuth and retrieve identity blocks data from the consent screen.

Simplified Usage:
    from sva_oauth_client import get_sva
    from sva_oauth_client.decorators import sva_oauth_required
    
    @sva_oauth_required
    def my_view(request):
        sva = get_sva(request)
        email = sva.get_block('email')
        blocks = sva.get_blocks()
"""

__version__ = '2.0.0'
__author__ = 'SVA Team'

# Core client and exceptions
from .client import SVAOAuthClient, SVATokenError, SVAOAuthError, SVAAuthorizationError

# Simplified facade (recommended)
from .facade import SVA, get_sva

# Decorators
from .decorators import sva_oauth_required, sva_blocks_required

# Configuration
from .config import SVAConfig

# Session management
from .session_manager import SVASessionManager

# Backward-compatible utilities
from .utils import (
    get_sva_claims,
    get_blocks_data,
    get_userinfo,
    get_access_token,
    get_data_token,
    is_authenticated,
    clear_oauth_session,
    get_client_from_settings,
)

__all__ = [
    # Core
    'SVAOAuthClient',
    'SVATokenError',
    'SVAOAuthError',
    'SVAAuthorizationError',
    
    # Simplified API (recommended)
    'SVA',
    'get_sva',
    
    # Configuration
    'SVAConfig',
    
    # Session management
    'SVASessionManager',
    
    # Decorators
    'sva_oauth_required',
    'sva_blocks_required',
    
    # Backward-compatible utilities
    'get_sva_claims',
    'get_blocks_data',
    'get_userinfo',
    'get_access_token',
    'get_data_token',
    'is_authenticated',
    'clear_oauth_session',
    'get_client_from_settings',
]


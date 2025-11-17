"""
SVA OAuth Client - A Django package for integrating SVA (Secure Vault Authentication) OAuth provider.

This package provides a complete solution for Django applications to authenticate users
via SVA OAuth and retrieve identity blocks data from the consent screen.
"""

__version__ = '1.0.1'
__author__ = 'SVA Team'

from .client import SVAOAuthClient, SVATokenError, SVAOAuthError, SVAAuthorizationError
from .decorators import sva_oauth_required, sva_blocks_required
from .utils import get_sva_claims, get_blocks_data, get_userinfo, get_access_token, get_data_token, is_authenticated, clear_oauth_session, get_client_from_settings

__all__ = [
    'SVAOAuthClient',
    'SVATokenError',
    'SVAOAuthError',
    'SVAAuthorizationError',
    'sva_oauth_required',
    'sva_blocks_required',
    'get_sva_claims',
    'get_blocks_data',
    'get_userinfo',
    'get_access_token',
    'get_data_token',
    'is_authenticated',
    'clear_oauth_session',
    'get_client_from_settings',
]


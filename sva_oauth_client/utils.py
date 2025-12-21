"""
Utility functions for SVA OAuth integration.

This module provides backward-compatible utility functions that wrap
the new session manager and facade for easier migration.
"""
import logging
from typing import Dict, Any, Optional
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest
from .client import SVAOAuthClient, SVATokenError
from .config import SVAConfig
from .session_manager import SVASessionManager
from .facade import SVA, get_sva

logger = logging.getLogger(__name__)


def get_client_from_settings() -> SVAOAuthClient:
    """
    Create SVAOAuthClient instance from Django settings.
    
    Returns:
        Configured SVAOAuthClient instance
        
    Raises:
        AttributeError: If required settings are missing
    """
    return SVAOAuthClient(
        base_url=SVAConfig.get_base_url(),
        client_id=SVAConfig.get_client_id(),
        client_secret=SVAConfig.get_client_secret(),
        redirect_uri=SVAConfig.get_redirect_uri(),
        data_token_secret=SVAConfig.get_data_token_secret(),
        data_token_algorithm=SVAConfig.get_data_token_algorithm(),
        scopes=SVAConfig.get_scopes()
    )


def get_sva_claims(request: HttpRequest) -> Optional[Dict[str, Any]]:
    """
    Retrieve and decode SVA claims from the cryptographically signed data_token.
    
    This function extracts the data_token from the session, verifies its signature
    and expiration, then returns the claims dictionary containing all user identity
    blocks. This is the stateless, efficient way to access user data without making
    separate API calls to a /userinfo endpoint.
    
    Args:
        request: Django HttpRequest object (must have session attribute)
        
    Returns:
        Dictionary containing SVA claims (identity blocks), or None if data_token
        is not present in session
        
    Raises:
        SVATokenError: If the data_token is invalid, expired, or has a bad signature.
                      This exception should be caught by middleware to trigger logout.
    
    Example:
        ```python
        from sva_oauth_client.utils import get_sva_claims
        
        @sva_oauth_required
        def my_view(request):
            claims = get_sva_claims(request)
            if claims:
                email = claims.get('email')
                name = claims.get('name')
                # Use claims directly - no API call needed!
        ```
    """
    session_mgr = SVASessionManager(request.session)
    return session_mgr.get_claims()


def get_access_token(session: SessionBase) -> Optional[str]:
    """
    Get access token from session.
    
    Args:
        session: Django session object
        
    Returns:
        Access token string, or None if not available
    """
    session_mgr = SVASessionManager(session)
    return session_mgr.get_access_token()


def get_data_token(session: SessionBase) -> Optional[str]:
    """
    Get data token from session.
    
    Args:
        session: Django session object
        
    Returns:
        Data token string, or None if not available
    """
    session_mgr = SVASessionManager(session)
    return session_mgr.get_data_token()


def is_authenticated(session: SessionBase) -> bool:
    """
    Check if user is authenticated with SVA OAuth.
    
    Args:
        session: Django session object
        
    Returns:
        True if authenticated, False otherwise
    """
    session_mgr = SVASessionManager(session)
    return session_mgr.is_authenticated()


def get_blocks_data(session: SessionBase) -> Optional[Dict[str, Any]]:
    """
    Get blocks data from session by decoding the data_token.
    
    This is a convenience function that extracts the data_token from the session
    and returns the decoded claims (identity blocks). This is the recommended
    way to access user identity blocks in views.
    
    Args:
        session: Django session object
        
    Returns:
        Dictionary containing identity blocks (claims), or None if data_token
        is not present in session
        
    Raises:
        SVATokenError: If the data_token is invalid, expired, or has a bad signature
        
    Example:
        ```python
        from sva_oauth_client.utils import get_blocks_data
        
        @sva_oauth_required
        def my_view(request):
            blocks_data = get_blocks_data(request.session)
            if blocks_data:
                email = blocks_data.get('email')
                name = blocks_data.get('name')
        ```
    """
    session_mgr = SVASessionManager(session)
    return session_mgr.get_blocks_data()


def get_userinfo(session: SessionBase, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get user information from session or fetch from OAuth provider.
    
    This function uses intelligent caching with sharing blob timestamp checking:
    - Caches userinfo in session to avoid repeated API calls
    - Checks blob timestamp to detect when user data was updated
    - Only fetches from API when blob timestamp changes or cache is missing
    - Supports force_refresh to bypass cache
    
    Args:
        session: Django session object
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Dictionary containing user information, or None if access token
        is not available. Includes:
        - Standard OAuth userinfo fields
        - blob_timestamp: When sharing blob was last updated
        - blob_updated: Whether blob was updated since last check
        
    Raises:
        SVATokenError: If the userinfo request fails
        
    Example:
        ```python
        from sva_oauth_client.utils import get_userinfo
        
        @sva_oauth_required
        def my_view(request):
            userinfo = get_userinfo(request.session)
            if userinfo:
                email = userinfo.get('email')
                sub = userinfo.get('sub')
                # Check if data was updated
                if userinfo.get('blob_updated'):
                    print("User data was updated!")
        ```
    """
    session_mgr = SVASessionManager(session)
    return session_mgr.get_userinfo(force_refresh=force_refresh)


def clear_oauth_session(session: SessionBase) -> None:
    """
    Clear all OAuth-related data from session, including cached userinfo and blob timestamp.
    
    Args:
        session: Django session object
    """
    session_mgr = SVASessionManager(session)
    session_mgr.clear()


"""
Utility functions for SVA OAuth integration.
"""
import logging
import jwt
from typing import Dict, Any, Optional
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest
from .client import SVAOAuthClient, SVATokenError

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
        base_url=getattr(settings, 'SVA_OAUTH_BASE_URL', 'http://localhost:8000'),
        client_id=getattr(settings, 'SVA_OAUTH_CLIENT_ID', ''),
        client_secret=getattr(settings, 'SVA_OAUTH_CLIENT_SECRET', ''),
        redirect_uri=getattr(settings, 'SVA_OAUTH_REDIRECT_URI', ''),
        data_token_secret=getattr(settings, 'SVA_DATA_TOKEN_SECRET', ''),
        data_token_algorithm=getattr(settings, 'SVA_DATA_TOKEN_ALGORITHM', 'HS256'),
        scopes=getattr(settings, 'SVA_OAUTH_SCOPES', None)
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
    # Retrieve data_token from session
    data_token = request.session.get('sva_oauth_data_token')
    if not data_token:
        logger.debug("No data_token found in session")
        return None
    
    # Retrieve secret from Django settings
    data_token_secret = getattr(settings, 'SVA_DATA_TOKEN_SECRET', None)
    if not data_token_secret:
        logger.error("SVA_DATA_TOKEN_SECRET not configured in settings")
        raise SVATokenError("SVA_DATA_TOKEN_SECRET not configured")
    
    # Get algorithm from settings (default to HS256)
    data_token_algorithm = getattr(settings, 'SVA_DATA_TOKEN_ALGORITHM', 'HS256')
    
    # Log configuration for debugging (without exposing the secret)
    logger.debug(f"Attempting to decode data_token with algorithm: {data_token_algorithm}")
    logger.debug(f"Data token length: {len(data_token) if data_token else 0}")
    logger.debug(f"Secret configured: {'Yes' if data_token_secret else 'No'} (length: {len(data_token_secret) if data_token_secret else 0})")
    
    try:
        # Decode and verify JWT
        # Verify signature and expiration, but not audience
        decoded = jwt.decode(
            data_token,
            data_token_secret,
            algorithms=[data_token_algorithm],
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,  # Disable audience validation
            }
        )
        
        # Extract claims from the decoded token
        claims = decoded.get('claims', {})
        logger.debug(f"Successfully decoded data_token. Claims keys: {list(claims.keys())}")
        return claims
        
    except jwt.ExpiredSignatureError:
        logger.warning("Data token has expired")
        raise SVATokenError("Data token has expired")
    except jwt.InvalidSignatureError:
        logger.error(
            f"Data token signature verification failed. "
            f"This usually means SVA_DATA_TOKEN_SECRET doesn't match the OAuth server's DATA_TOKEN_SECRET. "
            f"Algorithm: {data_token_algorithm}, Secret length: {len(data_token_secret)}"
        )
        raise SVATokenError("Invalid data token: Signature verification failed")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid data token: {str(e)}")
        raise SVATokenError(f"Invalid data token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error decoding data token: {e}", exc_info=True)
        raise SVATokenError(f"Failed to decode data token: {str(e)}")


def get_access_token(session: SessionBase) -> Optional[str]:
    """
    Get access token from session.
    
    Args:
        session: Django session object
        
    Returns:
        Access token string, or None if not available
    """
    return session.get('sva_oauth_access_token')


def get_data_token(session: SessionBase) -> Optional[str]:
    """
    Get data token from session.
    
    Args:
        session: Django session object
        
    Returns:
        Data token string, or None if not available
    """
    return session.get('sva_oauth_data_token')


def is_authenticated(session: SessionBase) -> bool:
    """
    Check if user is authenticated with SVA OAuth.
    
    Args:
        session: Django session object
        
    Returns:
        True if authenticated, False otherwise
    """
    return bool(session.get('sva_oauth_access_token'))


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
    data_token = session.get('sva_oauth_data_token')
    if not data_token:
        logger.debug("No data_token found in session")
        return None
    
    try:
        client = get_client_from_settings()
        return client.get_blocks_data(data_token)
    except SVATokenError:
        # Re-raise token errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting blocks data: {e}", exc_info=True)
        raise SVATokenError(f"Failed to get blocks data: {str(e)}")


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
    # Get access token from session
    access_token = session.get('sva_oauth_access_token')
    if not access_token:
        logger.debug("No access token found in session")
        return None
    
    # Get cached userinfo and blob timestamp
    cached_userinfo = session.get('sva_oauth_userinfo')
    cached_blob_timestamp = session.get('sva_oauth_blob_timestamp')
    
    # If we have cached data and not forcing refresh, check if we need to update
    if cached_userinfo and not force_refresh:
        # Check if blob timestamp is provided in cached data
        cached_timestamp = cached_userinfo.get('blob_timestamp') or cached_blob_timestamp
        
        if cached_timestamp:
            # Check with server if blob was updated
            try:
                client = get_client_from_settings()
                userinfo = client.get_userinfo(access_token, check_blob_timestamp=cached_timestamp)
                
                # Check if blob was updated
                new_timestamp = userinfo.get('blob_timestamp')
                blob_updated = new_timestamp and new_timestamp != cached_timestamp
                
                if blob_updated:
                    logger.info(f"Sharing blob updated: {cached_timestamp} -> {new_timestamp}")
                    # Update cache with new data
                    userinfo['blob_updated'] = True
                    session['sva_oauth_userinfo'] = userinfo
                    session['sva_oauth_blob_timestamp'] = new_timestamp
                    session.modified = True
                    return userinfo
                else:
                    # Blob hasn't changed, return cached data
                    logger.debug("Sharing blob unchanged, returning cached userinfo")
                    cached_userinfo['blob_updated'] = False
                    return cached_userinfo
            except SVATokenError:
                # If timestamp check fails, fall through to full fetch
                logger.warning("Blob timestamp check failed, fetching full userinfo")
        else:
            # No timestamp in cache, but we have cached data - return it
            logger.debug("Returning cached userinfo (no timestamp check)")
            return cached_userinfo
    
    # Fetch userinfo from OAuth provider (cache miss or force refresh)
    try:
        client = get_client_from_settings()
        userinfo = client.get_userinfo(access_token)
        
        # Extract and store blob timestamp if available
        blob_timestamp = userinfo.get('blob_timestamp')
        if blob_timestamp:
            session['sva_oauth_blob_timestamp'] = blob_timestamp
            userinfo['blob_updated'] = True  # First fetch is always "updated"
        else:
            userinfo['blob_updated'] = False
        
        # Cache userinfo in session for future requests
        session['sva_oauth_userinfo'] = userinfo
        session.modified = True
        
        logger.debug("Userinfo fetched and cached in session")
        return userinfo
        
    except SVATokenError:
        # Re-raise token errors
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting userinfo: {e}", exc_info=True)
        raise SVATokenError(f"Failed to get userinfo: {str(e)}")


def clear_oauth_session(session: SessionBase) -> None:
    """
    Clear all OAuth-related data from session, including cached userinfo and blob timestamp.
    
    Args:
        session: Django session object
    """
    keys_to_remove = [
        'sva_oauth_blob_timestamp',  # Clear blob timestamp cache
        'sva_oauth_access_token',
        'sva_oauth_refresh_token',
        'sva_oauth_data_token',
        'sva_oauth_userinfo',
        'sva_oauth_scope',
        'sva_oauth_code_verifier',
        'sva_oauth_state',
        'sva_access_token_expiry',
        'sva_remember_me',
    ]
    for key in keys_to_remove:
        session.pop(key, None)


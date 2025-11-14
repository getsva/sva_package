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


def clear_oauth_session(session: SessionBase) -> None:
    """
    Clear all OAuth-related data from session.
    
    Args:
        session: Django session object
    """
    keys_to_remove = [
        'sva_oauth_access_token',
        'sva_oauth_refresh_token',
        'sva_oauth_data_token',
        'sva_oauth_userinfo',
        'sva_oauth_scope',
        'sva_oauth_code_verifier',
        'sva_oauth_state',
    ]
    for key in keys_to_remove:
        session.pop(key, None)


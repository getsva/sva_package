"""
Token Refresh Middleware for SVA OAuth Client.

This middleware automatically refreshes access tokens before they expire,
providing a seamless user experience without requiring re-authentication.
"""

import logging
from datetime import datetime, timedelta, timezone
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.conf import settings

logger = logging.getLogger(__name__)


class TokenRefreshMiddleware(MiddlewareMixin):
    """
    Middleware that automatically refreshes OAuth access tokens before they expire.
    
    This middleware:
    1. Checks if the user has an access token in their session
    2. Verifies if the token is close to expiring (within 60 seconds)
    3. Silently refreshes the token using the refresh token
    4. Updates the session with new tokens and expiry time
    5. Handles refresh failures gracefully by logging out the user
    """
    
    def process_request(self, request):
        """
        Process each request to check and refresh tokens if needed.
        
        Args:
            request: Django HttpRequest object
            
        Returns:
            None (continues request processing) or HttpResponse (redirect on failure)
        """
        # Only run for requests that have tokens in session
        if 'sva_oauth_access_token' not in request.session:
            return None
        
        # Get token expiry from session
        access_token_expiry = request.session.get('sva_access_token_expiry')
        if not access_token_expiry:
            # No expiry stored, skip refresh check
            logger.debug("No token expiry timestamp in session, skipping refresh check")
            return None
        
        # Check if the token is close to expiring (within the next 60 seconds)
        expiry_datetime = datetime.fromtimestamp(access_token_expiry, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_until_expiry = (expiry_datetime - now).total_seconds()
        
        # Only refresh if token expires within 60 seconds
        if time_until_expiry > 60:
            # Token is still valid, no refresh needed
            return None
        
        logger.info(f"Access token expiring soon ({time_until_expiry:.0f} seconds), attempting refresh...")
        
        # Get refresh token from session
        refresh_token = request.session.get('sva_oauth_refresh_token')
        if not refresh_token:
            # No refresh token available, force logout
            logger.warning("No refresh token available, forcing logout")
            self._force_logout(request)
            return redirect(getattr(settings, 'SVA_OAUTH_LOGOUT_REDIRECT', '/'))
        
        try:
            # Import client here to avoid circular imports
            from .utils import get_client_from_settings
            
            # Get OAuth client instance
            client = get_client_from_settings()
            
            # Perform the silent refresh
            logger.info("Refreshing access token...")
            new_token_response = client.refresh_access_token(refresh_token)
            
            # Update the session with the new tokens
            request.session['sva_oauth_access_token'] = new_token_response.get('access_token')
            
            # The refresh token might also be rotated, so update it if it's in the response
            if 'refresh_token' in new_token_response:
                request.session['sva_oauth_refresh_token'] = new_token_response['refresh_token']
                logger.info("Refresh token rotated and updated")
            
            # Update data_token if provided
            if 'data_token' in new_token_response:
                request.session['sva_oauth_data_token'] = new_token_response['data_token']
            
            # Update the expiry timestamp
            new_expires_in = new_token_response.get('expires_in', 3600)  # Default to 1 hour
            new_expiry_timestamp = datetime.now(timezone.utc).timestamp() + new_expires_in
            request.session['sva_access_token_expiry'] = new_expiry_timestamp
            
            # Preserve the session expiry setting (Remember Me)
            # Don't reset it, just update the token expiry timestamp
            
            # Mark session as modified
            request.session.modified = True
            
            logger.info(f"Token refreshed successfully. New expiry in {new_expires_in} seconds")
            
        except Exception as e:
            # If refresh fails (e.g., refresh token is revoked or expired), force logout
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            self._force_logout(request)
            return redirect(getattr(settings, 'SVA_OAUTH_LOGOUT_REDIRECT', '/'))
        
        return None
    
    def _force_logout(self, request):
        """
        Clear all OAuth-related session data.
        
        Args:
            request: Django HttpRequest object
        """
        oauth_keys = [
            'sva_oauth_access_token',
            'sva_oauth_refresh_token',
            'sva_oauth_data_token',
            'sva_oauth_scope',
            'sva_access_token_expiry',
            'sva_remember_me',
        ]
        
        for key in oauth_keys:
            if key in request.session:
                del request.session[key]
        
        request.session.modified = True
        logger.info("OAuth session data cleared due to refresh failure")


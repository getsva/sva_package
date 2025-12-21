"""
Token Refresh Middleware for SVA OAuth Client.

This middleware automatically refreshes access tokens before they expire,
providing a seamless user experience without requiring re-authentication.
"""

import logging
import time
from datetime import datetime, timezone
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from .config import SVAConfig
from .session_manager import SVASessionManager

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
        # Skip token refresh during OAuth flow (login, callback, exchange)
        # These endpoints handle their own authentication flow
        oauth_paths = ['/oauth/login/', '/oauth/callback/', '/oauth/exchange/', '/oauth/logout/']
        if any(request.path.startswith(path) for path in oauth_paths):
            return None
        
        session_mgr = SVASessionManager(request.session)
        
        # Only run for requests that have tokens in session
        if not session_mgr.is_authenticated():
            return None
        
        # Get token expiry from session
        access_token_expiry = session_mgr.get_token_expiry()
        if not access_token_expiry:
            # No expiry stored, skip refresh check
            logger.debug("No token expiry timestamp in session, skipping refresh check")
            return None
        
        # Check if the token is close to expiring (within the next 60 seconds) or already expired
        expiry_datetime = datetime.fromtimestamp(access_token_expiry, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_until_expiry = (expiry_datetime - now).total_seconds()
        
        # Refresh if token expires within 60 seconds OR has already expired
        if time_until_expiry > 60:
            # Token is still valid, no refresh needed
            return None
        
        if time_until_expiry <= 0:
            logger.info(f"Access token has expired ({abs(time_until_expiry):.0f} seconds ago), attempting refresh...")
        else:
            logger.info(f"Access token expiring soon ({time_until_expiry:.0f} seconds), attempting refresh...")
        
        # Get refresh token from session
        refresh_token = session_mgr.get_refresh_token()
        if not refresh_token:
            # No refresh token available, force logout
            logger.warning("No refresh token available, forcing logout")
            session_mgr.clear()
            return redirect(SVAConfig.get_logout_redirect())
        
        # Rate limiting: Check if we've attempted too many refreshes recently
        refresh_attempts = request.session.get('_token_refresh_attempts', 0)
        last_refresh_attempt = request.session.get('_token_refresh_last_attempt', 0)
        current_time = time.time()
        
        # Reset counter if last attempt was more than 5 minutes ago
        if current_time - last_refresh_attempt > 300:
            refresh_attempts = 0
        
        # Rate limit: max 5 refresh attempts per 5 minutes
        if refresh_attempts >= 5:
            logger.warning(f"Token refresh rate limit exceeded ({refresh_attempts} attempts)")
            session_mgr.clear()
            next_url = request.get_full_path()
            login_url = SVAConfig.get_login_url()
            if next_url and next_url != login_url and not next_url.startswith('/oauth/'):
                from django.utils.http import urlencode
                redirect_url = f"{login_url}?{urlencode({'next': next_url})}"
            else:
                redirect_url = SVAConfig.get_logout_redirect()
            return redirect(redirect_url)
        
        # Check if refresh is already in progress (race condition prevention)
        refresh_in_progress = request.session.get('_token_refresh_in_progress', False)
        refresh_lock_time = request.session.get('_token_refresh_lock_time', 0)
        
        # If lock exists and is less than 10 seconds old, wait for it to complete
        if refresh_in_progress and (current_time - refresh_lock_time) < 10:
            logger.debug("Token refresh already in progress, skipping duplicate refresh")
            return None
        
        # Set refresh lock
        request.session['_token_refresh_in_progress'] = True
        request.session['_token_refresh_lock_time'] = current_time
        request.session['_token_refresh_attempts'] = refresh_attempts + 1
        request.session['_token_refresh_last_attempt'] = current_time
        request.session.modified = True
        
        try:
            # Import client here to avoid circular imports
            from .utils import get_client_from_settings
            
            # Get OAuth client instance
            client = get_client_from_settings()
            
            # Perform the silent refresh
            logger.info("Refreshing access token...")
            new_token_response = client.refresh_access_token(refresh_token)
            
            # Update the session with the new tokens
            session_mgr.store_tokens(new_token_response)
            
            # The refresh token might also be rotated, so update it if it's in the response
            if 'refresh_token' in new_token_response:
                logger.info("Refresh token rotated and updated")
            
            new_expires_in = new_token_response.get('expires_in', 3600)
            logger.info(f"Token refreshed successfully. New expiry in {new_expires_in} seconds")
            
            # Reset refresh attempts on success
            request.session['_token_refresh_attempts'] = 0
            
        except Exception as e:
            # Check if this is a revoked token error
            error_msg = str(e).lower()
            is_revoked = any(keyword in error_msg for keyword in ['revoked', 'invalid_grant', 'invalid_token'])
            
            if is_revoked:
                logger.warning(f"Refresh token appears to be revoked: {e}")
                session_mgr.clear()
                next_url = request.get_full_path()
                login_url = SVAConfig.get_login_url()
                if next_url and next_url != login_url and not next_url.startswith('/oauth/'):
                    from django.utils.http import urlencode
                    redirect_url = f"{login_url}?{urlencode({'next': next_url})}"
                else:
                    redirect_url = SVAConfig.get_logout_redirect()
                return redirect(redirect_url)
            
            # If refresh fails (e.g., network error), log but don't clear session yet
            # Allow a few retries before giving up
            logger.error(f"Token refresh failed: {e}", exc_info=True)
            
            # If we've tried multiple times, give up and force re-login
            if refresh_attempts >= 3:
                logger.error("Token refresh failed multiple times, forcing logout")
                session_mgr.clear()
                next_url = request.get_full_path()
                login_url = SVAConfig.get_login_url()
                if next_url and next_url != login_url and not next_url.startswith('/oauth/'):
                    from django.utils.http import urlencode
                    redirect_url = f"{login_url}?{urlencode({'next': next_url})}"
                else:
                    redirect_url = SVAConfig.get_logout_redirect()
                return redirect(redirect_url)
        finally:
            # Always clear the refresh lock
            request.session.pop('_token_refresh_in_progress', None)
            request.session.pop('_token_refresh_lock_time', None)
            request.session.modified = True
        
        return None


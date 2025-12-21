"""
Session management for SVA OAuth Client.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest
from .config import SVAConfig
from .client import SVAOAuthClient, SVATokenError

logger = logging.getLogger(__name__)


class SVASessionManager:
    """
    Manages all OAuth-related session operations.
    
    Provides a clean API for storing, retrieving, and managing OAuth tokens
    and user data in Django sessions.
    """
    
    # Session keys
    ACCESS_TOKEN_KEY = 'sva_oauth_access_token'
    REFRESH_TOKEN_KEY = 'sva_oauth_refresh_token'
    DATA_TOKEN_KEY = 'sva_oauth_data_token'
    SCOPE_KEY = 'sva_oauth_scope'
    CODE_VERIFIER_KEY = 'sva_oauth_code_verifier'
    STATE_KEY = 'sva_oauth_state'
    EXPIRY_KEY = 'sva_access_token_expiry'
    REMEMBER_ME_KEY = 'sva_remember_me'
    USERINFO_KEY = 'sva_oauth_userinfo'
    BLOB_TIMESTAMP_KEY = 'sva_oauth_blob_timestamp'
    APPROVED_SCOPES_KEY = 'sva_oauth_approved_scopes'
    
    def __init__(self, session: SessionBase):
        """
        Initialize session manager.
        
        Args:
            session: Django session object
        """
        self.session = session
    
    def store_tokens(self, token_response: Dict[str, Any]) -> None:
        """
        Store OAuth tokens in session.
        
        Args:
            token_response: Token response from OAuth provider
        """
        self.session[self.ACCESS_TOKEN_KEY] = token_response.get('access_token')
        self.session[self.REFRESH_TOKEN_KEY] = token_response.get('refresh_token')
        self.session[self.DATA_TOKEN_KEY] = token_response.get('data_token', '')
        scope_text = token_response.get('scope', '')
        self.session[self.SCOPE_KEY] = scope_text
        
        # Store approved_scopes - use scope from token response as initial value
        # This will be updated when userinfo is fetched with actual approved_scopes
        if scope_text:
            self.session[self.APPROVED_SCOPES_KEY] = scope_text.split()
            logger.debug(f"Stored initial approved_scopes from token scope: {self.session[self.APPROVED_SCOPES_KEY]}")
        
        # Store expiry timestamp
        expires_in = token_response.get('expires_in', 3600)
        expiry_timestamp = datetime.now(timezone.utc).timestamp() + expires_in
        self.session[self.EXPIRY_KEY] = expiry_timestamp
        
        # Store token storage timestamp to avoid immediate refresh attempts
        self.session['_token_stored_at'] = datetime.now(timezone.utc).timestamp()
        
        self.session.modified = True
        logger.debug("Tokens stored in session")
    
    def get_access_token(self) -> Optional[str]:
        """Get access token from session."""
        token = self.session.get(self.ACCESS_TOKEN_KEY)
        # Ensure token is properly trimmed (no extra whitespace)
        return token.strip() if token else None
    
    def get_refresh_token(self) -> Optional[str]:
        """Get refresh token from session."""
        return self.session.get(self.REFRESH_TOKEN_KEY)
    
    def get_data_token(self) -> Optional[str]:
        """Get data token from session."""
        return self.session.get(self.DATA_TOKEN_KEY)
    
    def get_claims(self, filter_by_approved_scopes: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get and decode claims from data_token.
        
        Args:
            filter_by_approved_scopes: If True, filter claims by approved scopes from session
        
        Returns:
            Dictionary containing claims, or None if data_token is not present
            
        Raises:
            SVATokenError: If token is invalid or expired
        """
        data_token = self.get_data_token()
        if not data_token:
            logger.debug("No data_token found in session")
            return None
        
        try:
            client = SVAOAuthClient(
                base_url=SVAConfig.get_base_url(),
                client_id=SVAConfig.get_client_id(),
                client_secret=SVAConfig.get_client_secret(),
                redirect_uri=SVAConfig.get_redirect_uri(),
                data_token_secret=SVAConfig.get_data_token_secret(),
                data_token_algorithm=SVAConfig.get_data_token_algorithm(),
                scopes=SVAConfig.get_scopes()
            )
            decoded = client.decode_data_token(data_token)
            all_claims = decoded.get('claims', {})
            
            # Filter claims by approved scopes if requested
            if filter_by_approved_scopes:
                # Get approved scopes from session (stored from userinfo) or use token scope as fallback
                approved_scopes = self.session.get(self.APPROVED_SCOPES_KEY)
                if not approved_scopes:
                    # Fallback to token scope (what was granted)
                    scope_text = self.session.get(self.SCOPE_KEY, '')
                    approved_scopes = set(scope_text.split()) if scope_text else set()
                    logger.debug(f"No approved_scopes in session, using token scope: {approved_scopes}")
                else:
                    approved_scopes = set(approved_scopes) if isinstance(approved_scopes, list) else set(approved_scopes.split())
                
                # Filter claims to only include approved scopes
                # Always include 'sub' if present (standard OAuth field)
                filtered_claims = {}
                if 'sub' in all_claims:
                    filtered_claims['sub'] = all_claims['sub']
                
                # Map scope names to claim keys (some scopes map to multiple claims)
                scope_to_claims = {
                    'openid': ['sub'],
                    'email': ['email', 'email_verified'],
                    'profile': ['name', 'given_name', 'family_name'],
                    'username': ['username'],
                    'name': ['name', 'given_name', 'family_name'],
                    'bio': ['bio'],
                    'address': ['address'],
                    'social': ['social'],
                    'images': ['images'],
                    'pronoun': ['pronoun'],
                    'dob': ['dob', 'date_of_birth'],
                    'skills': ['skills'],
                    'hobby': ['hobby', 'hobbies'],
                    'phone': ['phone', 'phone_number'],
                    'pan_card': ['pan_card', 'pan'],
                    'crypto_wallet': ['crypto_wallet', 'wallet'],
                    'education': ['education'],
                    'employment': ['employment'],
                    'professional_license': ['professional_license', 'license'],
                    'aadhar': ['aadhar', 'aadhaar'],
                    'driving_license': ['driving_license', 'driving_licence'],
                    'voter_id': ['voter_id', 'voterid'],
                    'passport': ['passport'],
                }
                
                # Build set of allowed claim keys based on approved scopes
                allowed_claim_keys = set()
                for scope in approved_scopes:
                    if scope in scope_to_claims:
                        allowed_claim_keys.update(scope_to_claims[scope])
                    else:
                        # If scope name matches claim key directly, allow it
                        allowed_claim_keys.add(scope)
                
                # Filter claims
                for key, value in all_claims.items():
                    if key in allowed_claim_keys or key == 'sub':
                        filtered_claims[key] = value
                
                logger.debug(f"Filtered claims from {len(all_claims)} to {len(filtered_claims)} based on approved scopes: {approved_scopes}")
                return filtered_claims
            
            return all_claims
        except SVATokenError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error decoding data token: {e}", exc_info=True)
            raise SVATokenError(f"Failed to decode data token: {str(e)}")
    
    def get_blocks_data(self) -> Optional[Dict[str, Any]]:
        """
        Get blocks data (claims) from session.
        
        Returns:
            Dictionary containing identity blocks, or None if not available
            
        Raises:
            SVATokenError: If token is invalid or expired
        """
        return self.get_claims()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return bool(self.get_access_token())
    
    def get_userinfo(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get userinfo from session cache or fetch from provider.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing user information, or None if not available
            
        Raises:
            SVATokenError: If request fails
        """
        access_token = self.get_access_token()
        if not access_token:
            logger.warning("No access token found in session when trying to get userinfo")
            return None
        
        # Log token info for debugging
        logger.debug(f"Getting userinfo - access token present: {bool(access_token)}, length: {len(access_token) if access_token else 0}")
        
            # Get cached userinfo (with cleanup of old cache if needed)
        cached_userinfo = self.session.get(self.USERINFO_KEY)
        cached_blob_timestamp = self.session.get(self.BLOB_TIMESTAMP_KEY)
        
        # Cleanup: Remove cache if it's older than 24 hours (prevent stale data)
        cache_timestamp = self.session.get('_userinfo_cache_timestamp')
        if cache_timestamp:
            cache_age = datetime.now(timezone.utc).timestamp() - cache_timestamp
            if cache_age > 86400:  # 24 hours
                logger.debug("Userinfo cache is older than 24 hours, clearing it")
                cached_userinfo = None
                cached_blob_timestamp = None
                self.session.pop(self.USERINFO_KEY, None)
                self.session.pop(self.BLOB_TIMESTAMP_KEY, None)
                self.session.pop('_userinfo_cache_timestamp', None)
        
        # Return cached data if available and not forcing refresh
        if cached_userinfo and not force_refresh:
            cached_timestamp = cached_userinfo.get('blob_timestamp') or cached_blob_timestamp
            
            if cached_timestamp:
                # Check if blob was updated
                try:
                    client = SVAOAuthClient(
                        base_url=SVAConfig.get_base_url(),
                        client_id=SVAConfig.get_client_id(),
                        client_secret=SVAConfig.get_client_secret(),
                        redirect_uri=SVAConfig.get_redirect_uri(),
                        data_token_secret=SVAConfig.get_data_token_secret(),
                        data_token_algorithm=SVAConfig.get_data_token_algorithm(),
                        scopes=SVAConfig.get_scopes()
                    )
                    userinfo = client.get_userinfo(access_token, check_blob_timestamp=cached_timestamp)
                    
                    new_timestamp = userinfo.get('blob_timestamp')
                    blob_updated = new_timestamp and new_timestamp != cached_timestamp
                    
                    if blob_updated:
                        logger.info(f"Sharing blob updated: {cached_timestamp} -> {new_timestamp}")
                        userinfo['blob_updated'] = True
                        self.session[self.USERINFO_KEY] = userinfo
                        self.session[self.BLOB_TIMESTAMP_KEY] = new_timestamp
                        self.session['_userinfo_cache_timestamp'] = datetime.now(timezone.utc).timestamp()
                        # Store approved_scopes if available
                        if '_approved_scopes' in userinfo:
                            self.session[self.APPROVED_SCOPES_KEY] = userinfo['_approved_scopes'] if isinstance(userinfo['_approved_scopes'], list) else userinfo['_approved_scopes'].split()
                        self.session.modified = True
                        return userinfo
                    else:
                        cached_userinfo['blob_updated'] = False
                        return cached_userinfo
                except SVATokenError as e:
                    # Check if this is likely an expired token error
                    error_msg = str(e).lower()
                    if 'expired' in error_msg or '401' in error_msg or 'unauthorized' in error_msg:
                        # Try to refresh the token and retry
                        logger.info("Access token appears expired during blob check, attempting to refresh...")
                        refresh_token = self.get_refresh_token()
                        if refresh_token:
                            try:
                                # Refresh the access token
                                new_token_response = client.refresh_access_token(refresh_token)
                                self.store_tokens(new_token_response)
                                
                                # Retry userinfo request with new token
                                new_access_token = new_token_response.get('access_token')
                                if new_access_token:
                                    logger.info("Token refreshed successfully, retrying blob timestamp check...")
                                    userinfo = client.get_userinfo(new_access_token, check_blob_timestamp=cached_timestamp)
                                    
                                    new_timestamp = userinfo.get('blob_timestamp')
                                    blob_updated = new_timestamp and new_timestamp != cached_timestamp
                                    
                                    if blob_updated:
                                        logger.info(f"Sharing blob updated: {cached_timestamp} -> {new_timestamp}")
                                        userinfo['blob_updated'] = True
                                        self.session[self.USERINFO_KEY] = userinfo
                                        self.session[self.BLOB_TIMESTAMP_KEY] = new_timestamp
                                        self.session['_userinfo_cache_timestamp'] = datetime.now(timezone.utc).timestamp()
                                        self.session.modified = True
                                        return userinfo
                                    else:
                                        cached_userinfo['blob_updated'] = False
                                        return cached_userinfo
                            except Exception as refresh_error:
                                logger.error(f"Token refresh failed during blob check: {refresh_error}", exc_info=True)
                                # Fall through to fetch full userinfo
                    logger.warning("Blob timestamp check failed, fetching full userinfo")
            else:
                return cached_userinfo
        
        # Fetch from provider
        try:
            # Log token info for debugging
            logger.debug(f"Fetching userinfo with access token (first 20 chars): {access_token[:20] if access_token else 'None'}...")
            logger.debug(f"Using base URL: {SVAConfig.get_base_url()}")
            
            client = SVAOAuthClient(
                base_url=SVAConfig.get_base_url(),
                client_id=SVAConfig.get_client_id(),
                client_secret=SVAConfig.get_client_secret(),
                redirect_uri=SVAConfig.get_redirect_uri(),
                data_token_secret=SVAConfig.get_data_token_secret(),
                data_token_algorithm=SVAConfig.get_data_token_algorithm(),
                scopes=SVAConfig.get_scopes()
            )
            logger.debug(f"Userinfo URL will be: {client.userinfo_url}")
            userinfo = client.get_userinfo(access_token)
            
            blob_timestamp = userinfo.get('blob_timestamp')
            if blob_timestamp:
                self.session[self.BLOB_TIMESTAMP_KEY] = blob_timestamp
                userinfo['blob_updated'] = True
            else:
                userinfo['blob_updated'] = False
            
            self.session[self.USERINFO_KEY] = userinfo
            self.session['_userinfo_cache_timestamp'] = datetime.now(timezone.utc).timestamp()
            
            # Extract and store approved_scopes from userinfo if available
            # This is used to filter data_token claims when userinfo is unavailable
            # Check if approved_scopes are in the userinfo response directly
            if '_approved_scopes' in userinfo:
                approved_scopes = userinfo['_approved_scopes']
                if approved_scopes:
                    self.session[self.APPROVED_SCOPES_KEY] = approved_scopes if isinstance(approved_scopes, list) else approved_scopes.split()
                    logger.debug(f"Stored approved_scopes from userinfo: {self.session[self.APPROVED_SCOPES_KEY]}")
            
            # Fallback: Use the scope from token response (represents what was granted)
            if self.APPROVED_SCOPES_KEY not in self.session:
                scope_text = self.session.get(self.SCOPE_KEY, '')
                if scope_text:
                    self.session[self.APPROVED_SCOPES_KEY] = scope_text.split()
                    logger.debug(f"Using token scope as approved_scopes fallback: {self.session[self.APPROVED_SCOPES_KEY]}")
            
            self.session.modified = True
            
            logger.debug("Userinfo fetched and cached in session")
            return userinfo
        except SVATokenError as e:
            # Check if this is likely an expired token error (401)
            error_msg = str(e).lower()
            if 'expired' in error_msg or '401' in error_msg or 'unauthorized' in error_msg:
                # Don't try to refresh if token was just stored - this is likely a userinfo endpoint issue
                # Only attempt refresh if token is actually expired (not just created)
                token_stored_at = self.session.get('_token_stored_at')
                should_refresh = True
                if token_stored_at:
                    time_since_stored = datetime.now(timezone.utc).timestamp() - token_stored_at
                    if time_since_stored < 10:  # Less than 10 seconds old
                        logger.debug(f"Token 401 error occurred {time_since_stored:.1f}s after storage. "
                                   f"Likely userinfo endpoint unavailable. Skipping refresh attempt.")
                        should_refresh = False
                
                if should_refresh:
                    # Try to refresh the token and retry
                    logger.info("Access token appears expired, attempting to refresh...")
                    refresh_token = self.get_refresh_token()
                    if refresh_token:
                        try:
                            # Refresh the access token
                            new_token_response = client.refresh_access_token(refresh_token)
                            self.store_tokens(new_token_response)
                            
                            # Retry userinfo request with new token
                            new_access_token = new_token_response.get('access_token')
                            if new_access_token:
                                logger.info("Token refreshed successfully, retrying userinfo request...")
                                userinfo = client.get_userinfo(new_access_token)
                                
                                blob_timestamp = userinfo.get('blob_timestamp')
                                if blob_timestamp:
                                    self.session[self.BLOB_TIMESTAMP_KEY] = blob_timestamp
                                    userinfo['blob_updated'] = True
                                else:
                                    userinfo['blob_updated'] = False
                                
                                self.session[self.USERINFO_KEY] = userinfo
                                self.session['_userinfo_cache_timestamp'] = datetime.now(timezone.utc).timestamp()
                                # Store approved_scopes if available
                                if '_approved_scopes' in userinfo:
                                    self.session[self.APPROVED_SCOPES_KEY] = userinfo['_approved_scopes'] if isinstance(userinfo['_approved_scopes'], list) else userinfo['_approved_scopes'].split()
                                self.session.modified = True
                                
                                logger.debug("Userinfo fetched and cached after token refresh")
                                return userinfo
                        except Exception as refresh_error:
                            logger.error(f"Token refresh failed: {refresh_error}", exc_info=True)
                            # If refresh fails, return None to allow fallback to data_token
                            # Don't raise error - let the system fall back gracefully
                            return None
                else:
                    # Token was just created, userinfo endpoint likely unavailable
                    # Return None to allow fallback to data_token
                    return None
            
            # If not an expired token error, or refresh failed, raise the original error
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting userinfo: {e}", exc_info=True)
            raise SVATokenError(f"Failed to get userinfo: {str(e)}")
    
    def clear(self) -> None:
        """Clear all OAuth-related data from session."""
        keys_to_remove = [
            self.BLOB_TIMESTAMP_KEY,
            self.ACCESS_TOKEN_KEY,
            self.REFRESH_TOKEN_KEY,
            self.DATA_TOKEN_KEY,
            self.USERINFO_KEY,
            self.SCOPE_KEY,
            self.CODE_VERIFIER_KEY,
            self.STATE_KEY,
            self.EXPIRY_KEY,
            self.REMEMBER_ME_KEY,
            '_token_stored_at',  # Clean up token storage timestamp
            '_token_refresh_in_progress',  # Clean up refresh lock
            '_token_refresh_attempts',  # Clean up refresh attempt counter
            '_token_refresh_last_attempt',  # Clean up refresh attempt timestamp
            '_token_refresh_lock_time',  # Clean up refresh lock timestamp
            '_userinfo_cache_timestamp',  # Clean up userinfo cache timestamp
            self.APPROVED_SCOPES_KEY,  # Clean up approved scopes
        ]
        for key in keys_to_remove:
            self.session.pop(key, None)
        self.session.modified = True
        logger.debug("OAuth session data cleared")
    
    def store_pkce_data(self, code_verifier: str, state: str) -> None:
        """Store PKCE data in session."""
        self.session[self.CODE_VERIFIER_KEY] = code_verifier
        self.session[self.STATE_KEY] = state
        self.session.modified = True
    
    def get_pkce_data(self) -> tuple[Optional[str], Optional[str]]:
        """Get PKCE data from session."""
        return (
            self.session.get(self.CODE_VERIFIER_KEY),
            self.session.get(self.STATE_KEY)
        )
    
    def set_remember_me(self, remember: bool) -> None:
        """Set remember me preference."""
        self.session[self.REMEMBER_ME_KEY] = remember
        self.session.modified = True
    
    def get_remember_me(self) -> bool:
        """Get remember me preference."""
        return self.session.get(self.REMEMBER_ME_KEY, False)
    
    def get_token_expiry(self) -> Optional[float]:
        """Get token expiry timestamp."""
        return self.session.get(self.EXPIRY_KEY)
    
    def update_token_expiry(self, expires_in: int) -> None:
        """Update token expiry timestamp."""
        expiry_timestamp = datetime.now(timezone.utc).timestamp() + expires_in
        self.session[self.EXPIRY_KEY] = expiry_timestamp
        self.session.modified = True


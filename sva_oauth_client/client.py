"""
SVA OAuth Client - Core OAuth client implementation.
"""
import secrets
import hashlib
import base64
import jwt
import requests
from typing import Dict, Optional, Any
from urllib.parse import urlencode


class SVAOAuthError(Exception):
    """Base exception for SVA OAuth errors."""
    pass


class SVATokenError(SVAOAuthError):
    """Exception raised when token operations fail."""
    pass


class SVAAuthorizationError(SVAOAuthError):
    """Exception raised when authorization fails."""
    pass


class SVAOAuthClient:
    """
    SVA OAuth 2.0 Client with PKCE support.
    
    This client handles the complete OAuth 2.0 authorization code flow
    with PKCE (Proof Key for Code Exchange) for secure authentication.
    """
    
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        data_token_secret: str,
        data_token_algorithm: str = 'HS256',
        scopes: Optional[str] = None
    ):
        """
        Initialize SVA OAuth Client.
        
        Args:
            base_url: Base URL of SVA OAuth provider
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: Redirect URI registered in OAuth app
            data_token_secret: Secret key for decoding data_token JWT
            data_token_algorithm: JWT algorithm (default: HS256)
            scopes: Space-separated list of scopes to request
        """
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.data_token_secret = data_token_secret
        self.data_token_algorithm = data_token_algorithm
        self.scopes = scopes or 'openid email profile'
        
        # OAuth endpoints
        self.authorize_url = f"{self.base_url}/oauth/authorize/"
        self.token_url = f"{self.base_url}/oauth/token/"
        self.userinfo_url = f"{self.base_url}/oauth/userinfo/"
    
    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a random code verifier for PKCE."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Generate code challenge from verifier using S256."""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        code_verifier: Optional[str] = None,
        additional_params: Optional[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Generate authorization URL and code verifier.
        
        Args:
            state: Optional state parameter for CSRF protection
            code_verifier: Optional code verifier (generated if not provided)
            additional_params: Additional query parameters
            
        Returns:
            Tuple of (authorization_url, code_verifier)
        """
        if code_verifier is None:
            code_verifier = self.generate_code_verifier()
        
        code_challenge = self.generate_code_challenge(code_verifier)
        
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': self.scopes,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        if additional_params:
            params.update(additional_params)
        
        query_string = urlencode(params)
        authorization_url = f"{self.authorize_url}?{query_string}"
        
        return authorization_url, code_verifier
    
    def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token and data_token.
        
        Args:
            code: Authorization code from callback
            code_verifier: Code verifier used in authorization
            state: Optional state parameter for validation
            
        Returns:
            Dictionary containing tokens and metadata:
            {
                'access_token': str,
                'refresh_token': str,
                'data_token': str,
                'scope': str,
                'expires_in': int,
                'token_type': str
            }
            
        Raises:
            SVATokenError: If token exchange fails
        """
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code_verifier': code_verifier,
        }
        
        try:
            response = requests.post(self.token_url, data=token_data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get('error_description', error_json.get('error', error_detail))
                except:
                    error_detail = e.response.text
            raise SVATokenError(f"Failed to exchange token: {error_detail}") from e
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            Dictionary containing new tokens
            
        Raises:
            SVATokenError: If token refresh fails
        """
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        
        try:
            response = requests.post(self.token_url, data=token_data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get('error_description', error_json.get('error', error_detail))
                except:
                    error_detail = e.response.text
            raise SVATokenError(f"Failed to refresh token: {error_detail}") from e
    
    def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from OAuth provider.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            Dictionary containing user information
            
        Raises:
            SVATokenError: If userinfo request fails
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(self.userinfo_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get('error_description', error_json.get('error', error_detail))
                except:
                    error_detail = e.response.text
            raise SVATokenError(f"Failed to get userinfo: {error_detail}") from e
    
    def decode_data_token(self, data_token: str) -> Dict[str, Any]:
        """
        Decode and verify data_token JWT.
        
        Args:
            data_token: JWT data token from token response
            
        Returns:
            Decoded token payload containing claims (blocks data)
            
        Raises:
            SVATokenError: If token is invalid or expired
        """
        try:
            # Decode without audience validation (aud claim may not match client_id)
            # We only verify signature and expiration
            decoded = jwt.decode(
                data_token,
                self.data_token_secret,
                algorithms=[self.data_token_algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": False,  # Disable audience validation
                }
            )
            return decoded
        except jwt.ExpiredSignatureError:
            raise SVATokenError("Data token has expired")
        except jwt.InvalidTokenError as e:
            raise SVATokenError(f"Invalid data token: {str(e)}")
    
    def get_blocks_data(self, data_token: str) -> Dict[str, Any]:
        """
        Extract blocks data from data_token.
        
        Args:
            data_token: JWT data token from token response
            
        Returns:
            Dictionary containing identity blocks data (claims)
            
        Raises:
            SVATokenError: If token is invalid or expired
        """
        decoded = self.decode_data_token(data_token)
        return decoded.get('claims', {})


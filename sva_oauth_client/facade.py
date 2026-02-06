"""
Simplified facade for SVA OAuth Client.

This module provides a high-level, easy-to-use API that reduces boilerplate
and makes the package more accessible to developers.
"""
from typing import Optional, Dict, Any
from django.http import HttpRequest
from .client import SVAOAuthClient, SVATokenError
from .session_manager import SVASessionManager
from .config import SVAConfig


class SVA:
    """
    Simplified facade for SVA OAuth operations.
    
    This class provides a clean, easy-to-use API that handles all the
    complexity of OAuth flows, session management, and token handling.
    
    Usage:
        # In a view
        sva = SVA(request)
        
        # Check authentication
        if sva.is_authenticated():
            blocks = sva.get_blocks()
            userinfo = sva.get_userinfo()
        
        # Get client for custom operations
        client = sva.get_client()
    """
    
    def __init__(self, request: HttpRequest):
        """
        Initialize SVA facade with request.
        
        Args:
            request: Django HttpRequest object
        """
        self.request = request
        self.session = SVASessionManager(request.session)
        self._client: Optional[SVAOAuthClient] = None
    
    def get_client(self) -> SVAOAuthClient:
        """
        Get or create OAuth client instance.
        
        Returns:
            Configured SVAOAuthClient instance
        """
        if self._client is None:
            self._client = SVAOAuthClient(
                base_url=SVAConfig.get_base_url(),
                client_id=SVAConfig.get_client_id(),
                client_secret=SVAConfig.get_client_secret(),
                redirect_uri=SVAConfig.get_redirect_uri(),
                data_token_secret=SVAConfig.get_data_token_secret(),
                data_token_algorithm=SVAConfig.get_data_token_algorithm(),
                scopes=SVAConfig.get_scopes()
            )
        return self._client
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.session.is_authenticated()
    
    def get_blocks(self) -> Optional[Dict[str, Any]]:
        """
        Get identity blocks (claims) from session.
        
        Returns:
            Dictionary containing identity blocks, or None if not available
            
        Raises:
            SVATokenError: If token is invalid or expired
        """
        return self.session.get_blocks_data()
    
    def get_claims(self) -> Optional[Dict[str, Any]]:
        """
        Alias for get_blocks().
        
        Returns:
            Dictionary containing claims, or None if not available
        """
        return self.get_blocks()
    
    def get_userinfo(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get user information from session or provider.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Dictionary containing user information, or None if not available
            
        Raises:
            SVATokenError: If request fails
        """
        return self.session.get_userinfo(force_refresh=force_refresh)
    
    def get_access_token(self) -> Optional[str]:
        """Get access token from session."""
        return self.session.get_access_token()
    
    def get_data_token(self) -> Optional[str]:
        """Get data token from session."""
        return self.session.get_data_token()
    
    def has_block(self, block_name: str) -> bool:
        """
        Check if a specific identity block is available.
        
        Args:
            block_name: Name of the block to check
            
        Returns:
            True if block is available, False otherwise
        """
        try:
            blocks = self.get_blocks()
            return blocks is not None and block_name in blocks
        except SVATokenError:
            return False
    
    def get_block(self, block_name: str, default: Any = None) -> Any:
        """
        Get a specific identity block value.
        
        Args:
            block_name: Name of the block to retrieve
            default: Default value if block is not available
            
        Returns:
            Block value or default
        """
        try:
            blocks = self.get_blocks()
            if blocks:
                return blocks.get(block_name, default)
        except SVATokenError:
            pass
        return default
    
    def logout(self) -> None:
        """Clear OAuth session and logout user."""
        self.session.clear()
    
    def store_tokens(self, token_response: Dict[str, Any]) -> None:
        """
        Store OAuth tokens in session.
        
        Args:
            token_response: Token response from OAuth provider
        """
        self.session.store_tokens(token_response)
    
    def refresh_userinfo(self) -> Optional[Dict[str, Any]]:
        """
        Force refresh userinfo from provider.
        
        Returns:
            Dictionary containing fresh user information
        """
        return self.get_userinfo(force_refresh=True)


# Convenience function for quick access
def get_sva(request: HttpRequest) -> SVA:
    """
    Get SVA facade instance for request.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        SVA facade instance
        
    Example:
        from sva_oauth_client.facade import get_sva
        
        def my_view(request):
            sva = get_sva(request)
            if sva.is_authenticated():
                email = sva.get_block('email')
    """
    return SVA(request)







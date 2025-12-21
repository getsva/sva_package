"""
Configuration management for SVA OAuth Client.
"""
from typing import Optional
from django.conf import settings


class SVAConfig:
    """
    Centralized configuration manager for SVA OAuth Client.
    
    Provides easy access to all configuration settings with sensible defaults.
    """
    
    @staticmethod
    def get_base_url() -> str:
        """Get OAuth provider base URL."""
        return getattr(settings, 'SVA_OAUTH_BASE_URL', 'http://localhost:8000')
    
    @staticmethod
    def get_client_id() -> str:
        """Get OAuth client ID."""
        return getattr(settings, 'SVA_OAUTH_CLIENT_ID', '')
    
    @staticmethod
    def get_client_secret() -> str:
        """Get OAuth client secret."""
        return getattr(settings, 'SVA_OAUTH_CLIENT_SECRET', '')
    
    @staticmethod
    def get_redirect_uri() -> str:
        """Get OAuth redirect URI."""
        return getattr(settings, 'SVA_OAUTH_REDIRECT_URI', '')
    
    @staticmethod
    def get_data_token_secret() -> str:
        """Get data token secret for JWT verification."""
        return getattr(settings, 'SVA_DATA_TOKEN_SECRET', '')
    
    @staticmethod
    def get_data_token_algorithm() -> str:
        """Get JWT algorithm for data token."""
        return getattr(settings, 'SVA_DATA_TOKEN_ALGORITHM', 'HS256')
    
    @staticmethod
    def get_scopes() -> Optional[str]:
        """Get OAuth scopes."""
        return getattr(settings, 'SVA_OAUTH_SCOPES', None)
    
    @staticmethod
    def get_success_redirect() -> str:
        """Get success redirect URL."""
        return getattr(settings, 'SVA_OAUTH_SUCCESS_REDIRECT', '/')
    
    @staticmethod
    def get_error_redirect() -> str:
        """Get error redirect URL."""
        return getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/')
    
    @staticmethod
    def get_logout_redirect() -> str:
        """Get logout redirect URL."""
        return getattr(settings, 'SVA_OAUTH_LOGOUT_REDIRECT', '/')
    
    @staticmethod
    def get_login_url() -> str:
        """Get login URL."""
        return getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
    
    @staticmethod
    def validate() -> tuple[bool, list[str]]:
        """
        Validate that all required settings are configured.
        
        Returns:
            Tuple of (is_valid, list_of_missing_settings)
        """
        missing = []
        
        if not SVAConfig.get_client_id():
            missing.append('SVA_OAUTH_CLIENT_ID')
        if not SVAConfig.get_client_secret():
            missing.append('SVA_OAUTH_CLIENT_SECRET')
        if not SVAConfig.get_redirect_uri():
            missing.append('SVA_OAUTH_REDIRECT_URI')
        if not SVAConfig.get_data_token_secret():
            missing.append('SVA_DATA_TOKEN_SECRET')
        
        return len(missing) == 0, missing



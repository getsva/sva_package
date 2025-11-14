"""
Decorators for SVA OAuth integration.
"""
from functools import wraps
from typing import Callable, Any
from django.shortcuts import redirect
from django.contrib import messages
from django.conf import settings
from .utils import is_authenticated, get_sva_claims
from .client import SVATokenError


def sva_oauth_required(view_func: Callable) -> Callable:
    """
    Decorator to require SVA OAuth authentication.
    
    Redirects to login if user is not authenticated.
    
    Usage:
        @sva_oauth_required
        def my_view(request):
            # User is authenticated with SVA OAuth
            claims = get_sva_claims(request)
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_authenticated(request.session):
            login_url = getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
            messages.info(request, 'Please sign in with SVA to continue.')
            return redirect(login_url)
        return view_func(request, *args, **kwargs)
    return wrapper


def sva_blocks_required(*required_claims: str):
    """
    Decorator to require specific identity claims (blocks) in the data_token.
    
    Args:
        *required_claims: Claim names that must be present in the data_token
        
    Usage:
        @sva_blocks_required('email', 'name', 'phone')
        def my_view(request):
            # User has approved email, name, and phone claims
            claims = get_sva_claims(request)
            email = claims.get('email')
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not is_authenticated(request.session):
                login_url = getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
                messages.info(request, 'Please sign in with SVA to continue.')
                return redirect(login_url)
            
            try:
                claims = get_sva_claims(request)
                if not claims:
                    messages.error(request, 'No claims data available. Please sign in again.')
                    login_url = getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
                    return redirect(login_url)
                
                missing_claims = [claim for claim in required_claims if claim not in claims]
                if missing_claims:
                    messages.error(
                        request,
                        f'Missing required claims: {", ".join(missing_claims)}. '
                        'Please sign in again and approve all requested claims.'
                    )
                    login_url = getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
                    return redirect(login_url)
                
                return view_func(request, *args, **kwargs)
            except SVATokenError as e:
                # Token is invalid or expired - force logout
                messages.error(request, 'Your session has expired. Please sign in again.')
                login_url = getattr(settings, 'SVA_OAUTH_LOGIN_URL', '/oauth/login/')
                return redirect(login_url)
        return wrapper
    return decorator


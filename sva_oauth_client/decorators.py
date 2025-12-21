"""
Decorators for SVA OAuth integration.
"""
from functools import wraps
from typing import Callable, Any
from django.shortcuts import redirect
from django.contrib import messages
from .config import SVAConfig
from .session_manager import SVASessionManager
from .client import SVATokenError


def sva_oauth_required(view_func: Callable) -> Callable:
    """
    Decorator to require SVA OAuth authentication.
    
    Redirects to login if user is not authenticated.
    Also validates data_token and clears session if token is invalid.
    
    Usage:
        @sva_oauth_required
        def my_view(request):
            # User is authenticated with SVA OAuth
            from sva_oauth_client.facade import get_sva
            sva = get_sva(request)
            blocks = sva.get_blocks()
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        session_mgr = SVASessionManager(request.session)
        
        if not session_mgr.is_authenticated():
            login_url = SVAConfig.get_login_url()
            # Store current URL as 'next' parameter for redirect after login
            next_url = request.get_full_path()
            if next_url and next_url != login_url:
                from django.utils.http import urlencode
                login_url = f"{login_url}?{urlencode({'next': next_url})}"
            messages.info(request, 'Please sign in with SVA to continue.')
            return redirect(login_url)
        
        # Validate data_token - if invalid, clear session and redirect to login
        try:
            session_mgr.get_claims()
        except SVATokenError:
            # Token is invalid or expired - clear session and force re-login
            session_mgr.clear()
            login_url = SVAConfig.get_login_url()
            # Store current URL as 'next' parameter for redirect after login
            next_url = request.get_full_path()
            if next_url and next_url != login_url:
                from django.utils.http import urlencode
                login_url = f"{login_url}?{urlencode({'next': next_url})}"
            messages.error(request, 'Your session has expired. Please sign in again.')
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
            from sva_oauth_client.facade import get_sva
            sva = get_sva(request)
            email = sva.get_block('email')
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            session_mgr = SVASessionManager(request.session)
            
            if not session_mgr.is_authenticated():
                login_url = SVAConfig.get_login_url()
                # Store current URL as 'next' parameter for redirect after login
                next_url = request.get_full_path()
                if next_url and next_url != login_url:
                    from django.utils.http import urlencode
                    login_url = f"{login_url}?{urlencode({'next': next_url})}"
                messages.info(request, 'Please sign in with SVA to continue.')
                return redirect(login_url)
            
            try:
                claims = session_mgr.get_claims()
                if not claims:
                    messages.error(request, 'No claims data available. Please sign in again.')
                    login_url = SVAConfig.get_login_url()
                    # Store current URL as 'next' parameter
                    next_url = request.get_full_path()
                    if next_url and next_url != login_url:
                        from django.utils.http import urlencode
                        login_url = f"{login_url}?{urlencode({'next': next_url})}"
                    return redirect(login_url)
                
                missing_claims = [claim for claim in required_claims if claim not in claims]
                if missing_claims:
                    messages.error(
                        request,
                        f'Missing required claims: {", ".join(missing_claims)}. '
                        'Please sign in again and approve all requested claims.'
                    )
                    login_url = SVAConfig.get_login_url()
                    # Store current URL as 'next' parameter
                    next_url = request.get_full_path()
                    if next_url and next_url != login_url:
                        from django.utils.http import urlencode
                        login_url = f"{login_url}?{urlencode({'next': next_url})}"
                    return redirect(login_url)
                
                return view_func(request, *args, **kwargs)
            except SVATokenError:
                # Token is invalid or expired - clear session and force logout
                session_mgr.clear()
                messages.error(request, 'Your session has expired. Please sign in again.')
                login_url = SVAConfig.get_login_url()
                # Store current URL as 'next' parameter
                next_url = request.get_full_path()
                if next_url and next_url != login_url:
                    from django.utils.http import urlencode
                    login_url = f"{login_url}?{urlencode({'next': next_url})}"
                return redirect(login_url)
        return wrapper
    return decorator


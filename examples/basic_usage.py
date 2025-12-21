"""
Basic usage example for sva-oauth-client package.

This file demonstrates both the new simplified API and the
backward-compatible utility functions.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from sva_oauth_client.decorators import sva_oauth_required, sva_blocks_required
from sva_oauth_client.utils import (
    get_blocks_data,
    get_userinfo,
    is_authenticated,
    clear_oauth_session
)
# New simplified API (recommended)
from sva_oauth_client import get_sva


# Example 1: Simple protected view
@sva_oauth_required
def dashboard(request):
    """Dashboard view that requires SVA OAuth authentication."""
    blocks_data = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    context = {
        'blocks': blocks_data or {},
        'userinfo': userinfo or {},
        'is_authenticated': is_authenticated(request.session),
    }
    
    return render(request, 'dashboard.html', context)


# Example 2: View requiring specific blocks
@sva_blocks_required('email', 'name', 'phone')
def profile(request):
    """Profile view that requires email, name, and phone blocks."""
    blocks_data = get_blocks_data(request.session)
    
    context = {
        'email': blocks_data.get('email'),
        'name': blocks_data.get('name'),
        'phone': blocks_data.get('phone'),
    }
    
    return render(request, 'profile.html', context)


# Example 3: Manual authentication check
def home(request):
    """Home page with login button."""
    if is_authenticated(request.session):
        return redirect('dashboard')
    
    return render(request, 'home.html')


# Example 4: Logout view
def logout(request):
    """Logout and clear OAuth session."""
    clear_oauth_session(request.session)
    messages.success(request, 'Successfully logged out.')
    return redirect('home')


# Example 5: View with conditional blocks
@sva_oauth_required
def settings(request):
    """Settings view that uses available blocks."""
    blocks_data = get_blocks_data(request.session) or {}
    
    # Check if specific blocks are available
    has_email = 'email' in blocks_data
    has_phone = 'phone' in blocks_data
    has_address = 'address' in blocks_data
    
    context = {
        'has_email': has_email,
        'has_phone': has_phone,
        'has_address': has_address,
        'email': blocks_data.get('email') if has_email else None,
        'phone': blocks_data.get('phone') if has_phone else None,
        'address': blocks_data.get('address') if has_address else None,
    }
    
    return render(request, 'settings.html', context)


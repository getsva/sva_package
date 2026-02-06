"""
Simplified usage examples for sva-oauth-client package.

This demonstrates the new simplified API that reduces boilerplate
and makes the package much easier to use.
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from sva_oauth_client import get_sva
from sva_oauth_client.decorators import sva_oauth_required, sva_blocks_required


# Example 1: Simple protected view with new simplified API
@sva_oauth_required
def dashboard(request):
    """Dashboard view using simplified API."""
    sva = get_sva(request)
    
    # Get all blocks at once
    blocks = sva.get_blocks()
    
    # Or get specific blocks easily
    email = sva.get_block('email')
    name = sva.get_block('name')
    phone = sva.get_block('phone')
    
    # Get userinfo
    userinfo = sva.get_userinfo()
    
    context = {
        'blocks': blocks or {},
        'userinfo': userinfo or {},
        'email': email,
        'name': name,
        'phone': phone,
    }
    
    return render(request, 'dashboard.html', context)


# Example 2: View requiring specific blocks
@sva_blocks_required('email', 'name', 'phone')
def profile(request):
    """Profile view that requires email, name, and phone blocks."""
    sva = get_sva(request)
    
    # Blocks are guaranteed to be available
    email = sva.get_block('email')
    name = sva.get_block('name')
    phone = sva.get_block('phone')
    
    context = {
        'email': email,
        'name': name,
        'phone': phone,
    }
    
    return render(request, 'profile.html', context)


# Example 3: Check authentication and blocks
def home(request):
    """Home page with login button."""
    sva = get_sva(request)
    
    if sva.is_authenticated():
        # Check if specific blocks are available
        has_email = sva.has_block('email')
        has_phone = sva.has_block('phone')
        
        context = {
            'has_email': has_email,
            'has_phone': has_phone,
        }
        return render(request, 'authenticated_home.html', context)
    
    return render(request, 'home.html')


# Example 4: Logout view
def logout(request):
    """Logout and clear OAuth session."""
    sva = get_sva(request)
    sva.logout()
    messages.success(request, 'Successfully logged out.')
    return redirect('home')


# Example 5: Conditional block access
@sva_oauth_required
def settings(request):
    """Settings view that uses available blocks."""
    sva = get_sva(request)
    
    # Check which blocks are available
    has_email = sva.has_block('email')
    has_phone = sva.has_block('phone')
    has_address = sva.has_block('address')
    
    # Get blocks with defaults
    email = sva.get_block('email', default='Not provided')
    phone = sva.get_block('phone', default='Not provided')
    address = sva.get_block('address', default='Not provided')
    
    context = {
        'has_email': has_email,
        'has_phone': has_phone,
        'has_address': has_address,
        'email': email,
        'phone': phone,
        'address': address,
    }
    
    return render(request, 'settings.html', context)


# Example 6: Force refresh userinfo
@sva_oauth_required
def refresh_profile(request):
    """Refresh user profile data."""
    sva = get_sva(request)
    
    # Force refresh userinfo from provider
    userinfo = sva.refresh_userinfo()
    
    if userinfo and userinfo.get('blob_updated'):
        messages.success(request, 'Profile updated!')
    
    return redirect('profile')


# Example 7: Access client for custom operations
@sva_oauth_required
def custom_operation(request):
    """View that uses client for custom operations."""
    sva = get_sva(request)
    client = sva.get_client()
    
    # Use client for custom operations
    access_token = sva.get_access_token()
    if access_token:
        # Custom API call using access token
        userinfo = client.get_userinfo(access_token)
        # ... custom logic
    
    return render(request, 'custom.html', {})







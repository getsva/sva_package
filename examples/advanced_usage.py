"""
Advanced usage examples for sva-oauth-client package.
"""
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from sva_oauth_client import SVAOAuthClient
from sva_oauth_client.client import SVATokenError, SVAAuthorizationError
from sva_oauth_client.utils import get_client_from_settings


# Example 1: Custom OAuth flow with manual client
@require_http_methods(["GET"])
def custom_login(request):
    """Custom login view with manual client initialization."""
    client = get_client_from_settings()
    
    # Generate authorization URL with custom state
    custom_state = f"custom_state_{request.user.id if request.user.is_authenticated else 'anonymous'}"
    auth_url, code_verifier = client.get_authorization_url(state=custom_state)
    
    # Store code_verifier in session
    request.session['custom_code_verifier'] = code_verifier
    request.session['custom_state'] = custom_state
    
    return redirect(auth_url)


@require_http_methods(["GET"])
def custom_callback(request):
    """Custom callback with manual token exchange."""
    code = request.GET.get('code')
    state = request.GET.get('state')
    code_verifier = request.session.get('custom_code_verifier')
    
    if not code or not code_verifier:
        return JsonResponse({'error': 'Missing code or code_verifier'}, status=400)
    
    # Verify state
    expected_state = request.session.get('custom_state')
    if state != expected_state:
        return JsonResponse({'error': 'Invalid state'}, status=400)
    
    try:
        client = get_client_from_settings()
        tokens = client.exchange_code_for_tokens(code, code_verifier, state)
        
        # Store tokens
        request.session['sva_oauth_access_token'] = tokens['access_token']
        request.session['sva_oauth_data_token'] = tokens.get('data_token', '')
        
        # Get blocks data
        blocks_data = client.get_blocks_data(tokens['data_token'])
        
        return JsonResponse({
            'success': True,
            'blocks': blocks_data,
        })
        
    except SVATokenError as e:
        return JsonResponse({'error': str(e)}, status=400)


# Example 2: Token refresh
@require_http_methods(["POST"])
def refresh_token(request):
    """Refresh access token using refresh token."""
    refresh_token = request.session.get('sva_oauth_refresh_token')
    
    if not refresh_token:
        return JsonResponse({'error': 'No refresh token'}, status=400)
    
    try:
        client = get_client_from_settings()
        new_tokens = client.refresh_access_token(refresh_token)
        
        # Update session
        request.session['sva_oauth_access_token'] = new_tokens['access_token']
        if 'refresh_token' in new_tokens:
            request.session['sva_oauth_refresh_token'] = new_tokens['refresh_token']
        
        return JsonResponse({'success': True})
        
    except SVATokenError as e:
        return JsonResponse({'error': str(e)}, status=400)


# Example 3: API endpoint that returns blocks data
@require_http_methods(["GET"])
def api_blocks(request):
    """API endpoint that returns blocks data as JSON."""
    from sva_oauth_client.utils import get_blocks_data, is_authenticated
    
    if not is_authenticated(request.session):
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    blocks_data = get_blocks_data(request.session)
    
    if not blocks_data:
        return JsonResponse({'error': 'No blocks data available'}, status=404)
    
    return JsonResponse({
        'success': True,
        'blocks': blocks_data,
    })


# Example 4: View with error handling
def safe_dashboard(request):
    """Dashboard with comprehensive error handling."""
    from sva_oauth_client.utils import (
        get_blocks_data,
        get_userinfo,
        is_authenticated,
        get_client_from_settings
    )
    
    if not is_authenticated(request.session):
        return redirect('sva_oauth_client:login')
    
    try:
        blocks_data = get_blocks_data(request.session)
        userinfo = get_userinfo(request.session)
        
        # Validate data_token if needed
        data_token = request.session.get('sva_oauth_data_token')
        if data_token:
            client = get_client_from_settings()
            try:
                decoded = client.decode_data_token(data_token)
                # Use decoded token data
            except SVATokenError:
                # Token expired or invalid, redirect to login
                return redirect('sva_oauth_client:login')
        
        context = {
            'blocks': blocks_data or {},
            'userinfo': userinfo or {},
        }
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        # Log error and show user-friendly message
        return render(request, 'error.html', {
            'error': 'An error occurred while loading your data.',
        })


# Example 5: Conditional block access
def conditional_view(request):
    """View that conditionally requires blocks based on feature."""
    from sva_oauth_client.utils import get_blocks_data, is_authenticated
    
    if not is_authenticated(request.session):
        return redirect('sva_oauth_client:login')
    
    blocks_data = get_blocks_data(request.session) or {}
    
    # Check which features are available based on blocks
    features = {
        'email_verification': 'email' in blocks_data,
        'phone_verification': 'phone' in blocks_data,
        'kyc_verification': 'pan_card' in blocks_data or 'aadhar' in blocks_data,
        'profile_complete': all(key in blocks_data for key in ['name', 'email', 'bio']),
    }
    
    context = {
        'features': features,
        'blocks': blocks_data,
    }
    
    return render(request, 'features.html', context)


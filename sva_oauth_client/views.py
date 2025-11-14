"""
Django views for SVA OAuth integration.
"""
import logging
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .client import SVAOAuthClient, SVATokenError, SVAAuthorizationError
from .utils import get_client_from_settings, clear_oauth_session

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def oauth_login(request):
    """
    Initiate OAuth flow - Store remember_me preference and redirect to OAuth server.
    Client-side JavaScript will store PKCE data in localStorage and redirect.
    
    URL: /oauth/login/
    """
    try:
        # Handle POST request with remember_me checkbox
        if request.method == 'POST':
            remember_me = request.POST.get('remember_me') == 'true'
            # Store remember_me preference in session for later use in oauth_exchange
            request.session['sva_remember_me'] = remember_me
            request.session.modified = True
            logger.info(f"Remember me preference stored: {remember_me}")
        
        client = get_client_from_settings()
        
        # Generate state and code verifier
        import secrets
        state = secrets.token_urlsafe(32)
        code_verifier = None  # Let client generate it
        
        logger.info(f"Starting OAuth flow - state: {state[:20]}...")
        
        # Generate authorization URL
        auth_url, code_verifier = client.get_authorization_url(
            state=state,
            code_verifier=code_verifier
        )
        
        # Return a page that stores PKCE data in localStorage and redirects
        from django.http import HttpResponse
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting to SVA...</title>
        </head>
        <body>
            <script>
                // Store PKCE data in localStorage (temporary, only for OAuth flow)
                localStorage.setItem('sva_oauth_code_verifier', '{code_verifier}');
                localStorage.setItem('sva_oauth_state', '{state}');
                
                // Redirect to OAuth server
                window.location.href = '{auth_url}';
            </script>
            <p>Redirecting to SVA...</p>
        </body>
        </html>
        """
        return HttpResponse(html)
        
    except Exception as e:
        logger.error(f"Error in oauth_login: {str(e)}", exc_info=True)
        messages.error(request, f'Failed to initiate OAuth flow: {str(e)}')
        return redirect(getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/'))


@require_http_methods(["GET"])
def oauth_callback(request):
    """
    Handle OAuth callback - SIMPLE: Get code_verifier from localStorage via JavaScript.
    No session management needed!
    
    URL: /oauth/callback/
    """
    logger.info(f"OAuth callback received. Query params: {dict(request.GET)}")
    
    error = request.GET.get('error')
    if error:
        error_description = request.GET.get('error_description', error)
        logger.error(f"OAuth error in callback: {error} - {error_description}")
        # Return error page that shows message
        from django.http import HttpResponse
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
        </head>
        <body>
            <h1>OAuth Error</h1>
            <p>{error_description}</p>
            <a href="{getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/')}">Go Home</a>
        </body>
        </html>
        """
        return HttpResponse(html)
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    logger.info(f"Callback received - code: {'present' if code else 'missing'}, state: {state}")
    
    if not code:
        logger.warning("No authorization code in callback")
        from django.http import HttpResponse
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Error</title>
        </head>
        <body>
            <h1>OAuth Error</h1>
            <p>No authorization code received</p>
            <a href="{getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/')}">Go Home</a>
        </body>
        </html>
        """
        return HttpResponse(html)
    
    # SIMPLE: Return a page that reads from localStorage and exchanges token
    # Then stores tokens in session and redirects
    from django.http import HttpResponse
    success_url = getattr(settings, 'SVA_OAUTH_SUCCESS_REDIRECT', '/dashboard/')
    error_url = getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Completing OAuth...</title>
    </head>
    <body>
        <p>Completing authentication...</p>
        <script>
            // Get PKCE data from localStorage (simple!)
            const codeVerifier = localStorage.getItem('sva_oauth_code_verifier');
            const expectedState = localStorage.getItem('sva_oauth_state');
            const code = '{code}';
            const state = '{state}';
            
            // Verify state
            if (state !== expectedState) {{
                alert('Invalid state parameter. Security check failed.');
                localStorage.removeItem('sva_oauth_code_verifier');
                localStorage.removeItem('sva_oauth_state');
                window.location.href = '{error_url}';
            }} else if (!codeVerifier) {{
                alert('Missing code verifier. Please try signing in again.');
                window.location.href = '{error_url}';
            }} else {{
                // Exchange code for tokens via AJAX
                fetch('/oauth/exchange/', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    }},
                    body: JSON.stringify({{
                        code: code,
                        state: state,
                        code_verifier: codeVerifier
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        // Clear localStorage
                        localStorage.removeItem('sva_oauth_code_verifier');
                        localStorage.removeItem('sva_oauth_state');
                        // Redirect to success page
                        window.location.href = '{success_url}';
                    }} else {{
                        alert('Token exchange failed: ' + (data.error || 'Unknown error'));
                        localStorage.removeItem('sva_oauth_code_verifier');
                        localStorage.removeItem('sva_oauth_state');
                        window.location.href = '{error_url}';
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Failed to exchange token. Please try again.');
                    localStorage.removeItem('sva_oauth_code_verifier');
                    localStorage.removeItem('sva_oauth_state');
                    window.location.href = '{error_url}';
                }});
            }}
            
            function getCookie(name) {{
                let cookieValue = null;
                if (document.cookie && document.cookie !== '') {{
                    const cookies = document.cookie.split(';');
                    for (let i = 0; i < cookies.length; i++) {{
                        const cookie = cookies[i].trim();
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }}
                    }}
                }}
                return cookieValue;
            }}
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)


@csrf_exempt
@require_http_methods(["POST"])
def oauth_exchange(request):
    """
    Exchange authorization code for tokens - SIMPLE endpoint.
    Called by JavaScript from callback page.
    No session management for PKCE - it comes from request body!
    
    URL: /oauth/exchange/
    """
    import json
    from django.http import JsonResponse
    
    try:
        # Get data from request body
        data = json.loads(request.body)
        code = data.get('code')
        state = data.get('state')
        code_verifier = data.get('code_verifier')
        
        logger.info(f"Token exchange request - code: {'present' if code else 'missing'}, state: {state[:20] if state else 'missing'}...")
        
        if not code or not code_verifier:
            return JsonResponse({
                'success': False,
                'error': 'Missing code or code_verifier'
            }, status=400)
        
        # Exchange code for tokens
        client = get_client_from_settings()
        logger.info("Exchanging authorization code for tokens...")
        
        token_response = client.exchange_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            state=state
        )
        
        logger.info(f"Token exchange successful. Has access_token: {'access_token' in token_response}, Has data_token: {'data_token' in token_response}")
        
        data_token = token_response.get('data_token', '')
        logger.info(f"Data token received: {'Yes' if data_token else 'No'}, length: {len(data_token) if data_token else 0}")
        
        # Try to decode and log blocks data for debugging
        if data_token:
            try:
                decoded = client.decode_data_token(data_token)
                claims = decoded.get('claims', {})
                logger.info(f"Data token decoded successfully. Claims keys: {list(claims.keys()) if claims else 'None'}")
                logger.info(f"Number of blocks in claims: {len(claims)}")
            except Exception as e:
                logger.warning(f"Could not decode data token for logging: {e}")
        
        # Store tokens in session (only tokens, no PKCE data needed)
        request.session['sva_oauth_access_token'] = token_response.get('access_token')
        request.session['sva_oauth_refresh_token'] = token_response.get('refresh_token')
        request.session['sva_oauth_data_token'] = data_token
        request.session['sva_oauth_scope'] = token_response.get('scope', '')
        
        # Calculate and store token expiry timestamp for middleware
        expires_in = token_response.get('expires_in', 3600)  # Default to 1 hour if not provided
        from datetime import datetime, timezone
        expiry_timestamp = datetime.now(timezone.utc).timestamp() + expires_in
        request.session['sva_access_token_expiry'] = expiry_timestamp
        
        # Handle "Remember Me" - set session expiry based on user preference
        remember_me = request.session.get('sva_remember_me', False)
        if remember_me:
            # Set session to expire in 30 days (2592000 seconds)
            from datetime import timedelta
            request.session.set_expiry(timedelta(days=30).total_seconds())
            logger.info("Session set to expire in 30 days (Remember Me enabled)")
        else:
            # Set session to expire when browser closes (default secure behavior)
            request.session.set_expiry(0)
            logger.info("Session set to expire on browser close (Remember Me disabled)")
        
        # Clear the remember_me flag from session (no longer needed)
        if 'sva_remember_me' in request.session:
            del request.session['sva_remember_me']
        
        # CRITICAL: Mark session as modified and save to ensure persistence
        request.session.modified = True
        
        logger.info("Tokens stored in session with expiry timestamp")
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully authenticated with SVA!'
        })
        
    except SVATokenError as e:
        logger.error(f"Token exchange error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in exchange: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }, status=500)


@require_http_methods(["GET", "POST"])
def oauth_logout(request):
    """
    Logout and clear OAuth session data.
    
    URL: /oauth/logout/
    """
    clear_oauth_session(request.session)
    messages.success(request, 'Successfully logged out.')
    
    logout_redirect = getattr(settings, 'SVA_OAUTH_LOGOUT_REDIRECT', '/')
    return redirect(logout_redirect)


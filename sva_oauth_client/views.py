"""
Django views for SVA OAuth integration.
"""
import logging
import secrets
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core import signing
from django.http import JsonResponse
from django.utils.safestring import mark_safe
import json
from .client import SVATokenError
from .config import SVAConfig
from .session_manager import SVASessionManager
from .facade import SVA

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def oauth_login(request):
    """
    Initiate OAuth flow using STATELESS verification.
    We sign the state parameter cryptographically so we verify it on return 
    without needing a session cookie for the initial handshake.
    This fixes issues with cross-domain/popup cookie blocking.
    """
    try:
        # Handle POST request with remember_me checkbox
        session_mgr = SVASessionManager(request.session)
        if request.method == 'POST':
            remember_me = request.POST.get('remember_me') == 'true'
            session_mgr.set_remember_me(remember_me)
        
        # Store 'next' parameter if provided (for redirect after successful login)
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url:
            # Store in session for use after successful authentication
            request.session['oauth_next_url'] = next_url
            logger.info(f"Stored next URL for redirect after login: {next_url}")
        
        sva = SVA(request)
        client = sva.get_client()
        
        # 1. Generate a random value
        random_token = secrets.token_urlsafe(32)
        
        # 2. Cryptographically sign it.
        #    This allows us to verify it later without storing anything in the session.
        signed_state = signing.dumps(random_token)
        
        # 3. Use None for code_verifier (letting client JS generate it for PKCE)
        code_verifier = None 
        
        logger.info(f"Starting Stateless OAuth flow - signed_state length: {len(signed_state)}")
        
        # 4. Generate authorization URL with the SIGNED state
        auth_url, code_verifier = client.get_authorization_url(
            state=signed_state,
            code_verifier=code_verifier
        )
        
        # 5. Return template with safe JSON strings
        return render(request, 'sva_oauth_client/oauth_redirect.html', {
            'code_verifier': mark_safe(json.dumps(code_verifier)),
            'state': mark_safe(json.dumps(signed_state)),
            'auth_url': mark_safe(json.dumps(auth_url)),
        })
        
    except Exception as e:
        logger.error(f"Error in oauth_login: {str(e)}", exc_info=True)
        return redirect(SVAConfig.get_error_redirect())

@require_http_methods(["GET"])
def oauth_callback(request):
    """
    Handle OAuth callback - Validate signed state, then exchange token.
    This endpoint doesn't require an active session, as it's the start of a new auth flow.
    If there's an expired session, we clear it to start fresh.
    """
    error = request.GET.get('error')
    if error:
        error_desc = request.GET.get('error_description', error)
        # Clear any existing session on error
        session_mgr = SVASessionManager(request.session)
        session_mgr.clear()
        return render_error(request, f"OAuth Error: {error_desc}")
    
    code = request.GET.get('code')
    signed_state = request.GET.get('state')
    
    if not code or not signed_state:
        return render_error(request, "Missing authorization code or state parameter.")
    
    # CRITICAL: Validate the signed state.
    try:
        # max_age=600 ensures the link expires after 10 minutes
        original_token = signing.loads(signed_state, max_age=600)
        logger.info("State signature verified successfully (Stateless).")
    except signing.SignatureExpired:
        logger.warning("OAuth login attempt expired.")
        # Clear any existing session
        session_mgr = SVASessionManager(request.session)
        session_mgr.clear()
        return render_error(request, "Login attempt expired. Please try again.")
    except signing.BadSignature:
        logger.error("Invalid state signature! Potential tampering.")
        # Clear any existing session
        session_mgr = SVASessionManager(request.session)
        session_mgr.clear()
        return render_error(request, "Security check failed. Invalid state parameter.")
    
    # Don't clear existing session during callback - user might be re-authenticating
    # to update permissions. The new token exchange will overwrite old tokens anyway.
    # Only clear if there's an explicit error or the session is completely invalid.
    session_mgr = SVASessionManager(request.session)
    if session_mgr.is_authenticated():
        # Check if session is actually valid by trying to get claims
        try:
            session_mgr.get_claims()
            # Session is valid, keep it (user might be re-authenticating to update permissions)
            logger.info("Existing valid session found during callback - will be updated with new tokens")
        except SVATokenError:
            # Session exists but is expired/invalid, clear it
            logger.info("Clearing expired session before new authentication")
            session_mgr.clear()
    
    # Render the client-side exchange page
    success_url = SVAConfig.get_success_redirect()
    error_url = SVAConfig.get_error_redirect()
    
    return render(request, 'sva_oauth_client/oauth_callback.html', {
        'code': mark_safe(json.dumps(code)),
        'state': mark_safe(json.dumps(signed_state)),
        'success_url': mark_safe(json.dumps(success_url)),
        'error_url': mark_safe(json.dumps(error_url)),
    })

def render_error(request, message: str):
    """Render error page."""
    return render(request, 'sva_oauth_client/oauth_error.html', {
        'message': message
    })

@csrf_exempt
@require_http_methods(["POST"])
def oauth_exchange(request):
    """
    Exchange code for tokens.
    Validates state parameter and code verifier for security.
    """
    try:
        data = json.loads(request.body)
        code = data.get('code')
        state = data.get('state')
        code_verifier = data.get('code_verifier')
        
        # Validate required parameters
        if not code:
            logger.error("Token exchange failed: missing authorization code")
            return JsonResponse({'success': False, 'error': 'Missing authorization code'}, status=400)
        
        if not code_verifier:
            logger.error("Token exchange failed: missing code verifier")
            return JsonResponse({'success': False, 'error': 'Missing code verifier'}, status=400)
        
        if not state:
            logger.error("Token exchange failed: missing state parameter")
            return JsonResponse({'success': False, 'error': 'Missing state parameter'}, status=400)
        
        # Validate state parameter (should be signed)
        try:
            from django.core import signing
            # Verify the signed state
            signing.loads(state, max_age=600)
            logger.debug("State parameter validated successfully")
        except (signing.BadSignature, signing.SignatureExpired) as e:
            logger.error(f"Token exchange failed: invalid state parameter - {e}")
            return JsonResponse({'success': False, 'error': 'Invalid or expired state parameter'}, status=400)
        
        sva = SVA(request)
        client = sva.get_client()
        
        # Exchange code for tokens with retry logic for transient failures
        max_retries = 3
        retry_count = 0
        token_response = None
        
        while retry_count < max_retries:
            try:
                token_response = client.exchange_code_for_tokens(code=code, code_verifier=code_verifier, state=state)
                break
            except SVATokenError as e:
                error_msg = str(e).lower()
                # Retry on network errors or 5xx server errors
                if retry_count < max_retries - 1 and any(keyword in error_msg for keyword in ['timeout', 'connection', '500', '502', '503', '504']):
                    retry_count += 1
                    logger.warning(f"Token exchange failed (attempt {retry_count}/{max_retries}), retrying...")
                    import time
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                    continue
                else:
                    raise
        
        if not token_response:
            raise SVATokenError("Token exchange failed after retries")
        
        # Validate that we received required tokens
        if not token_response.get('access_token'):
            logger.error("Token exchange failed: no access token in response")
            return JsonResponse({'success': False, 'error': 'Invalid token response: missing access token'}, status=400)
        
        # Log token response for debugging (without exposing full tokens)
        logger.info(f"Token exchange successful - access_token present: {bool(token_response.get('access_token'))}, "
                   f"refresh_token present: {bool(token_response.get('refresh_token'))}, "
                   f"data_token present: {bool(token_response.get('data_token'))}, "
                   f"scopes: {token_response.get('scope', 'N/A')}")
        
        # Store tokens using session manager
        session_mgr = SVASessionManager(request.session)
        session_mgr.store_tokens(token_response)
        
        # Verify tokens were stored
        stored_access_token = session_mgr.get_access_token()
        logger.info(f"Tokens stored - access_token in session: {bool(stored_access_token)}, "
                   f"length: {len(stored_access_token) if stored_access_token else 0}")
        
        # Validate scopes if configured
        requested_scopes = SVAConfig.get_scopes()
        if requested_scopes:
            received_scopes = token_response.get('scope', '').split()
            requested_scope_list = requested_scopes.split()
            missing_scopes = set(requested_scope_list) - set(received_scopes)
            if missing_scopes:
                logger.warning(f"Some requested scopes were not granted: {missing_scopes}")
        
        # Get next URL from session if it was stored during login
        next_url = request.session.pop('oauth_next_url', None)
        response_data = {'success': True}
        if next_url:
            response_data['next_url'] = next_url
            logger.info(f"Returning next URL for redirect: {next_url}")
        
        return JsonResponse(response_data)
    except SVATokenError as e:
        logger.error(f"Token exchange error: {e}")
        return JsonResponse({'success': False, 'error': f'Token exchange failed: {str(e)}'}, status=400)
    except json.JSONDecodeError:
        logger.error("Token exchange failed: invalid JSON in request body")
        return JsonResponse({'success': False, 'error': 'Invalid request format'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected exchange error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred during token exchange'}, status=500)

@require_http_methods(["GET", "POST"])
def oauth_logout(request):
    """Logout and clear OAuth session."""
    sva = SVA(request)
    sva.logout()
    return redirect(SVAConfig.get_logout_redirect())

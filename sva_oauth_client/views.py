"""
Django views for SVA OAuth integration.
"""
import logging
import json
import secrets
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core import signing
from django.http import HttpResponse, JsonResponse
from .client import SVATokenError
from .utils import get_client_from_settings, clear_oauth_session

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
        if request.method == 'POST':
            remember_me = request.POST.get('remember_me') == 'true'
            request.session['sva_remember_me'] = remember_me
            request.session.modified = True
        
        client = get_client_from_settings()
        
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
        
        # 5. Return HTML to redirect. 
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Redirecting to SVA...</title>
        </head>
        <body>
            <script>
                // Store PKCE data in localStorage
                localStorage.setItem('sva_oauth_code_verifier', {json.dumps(code_verifier)});
                // Store state just in case, though server validates signature
                localStorage.setItem('sva_oauth_state', {json.dumps(signed_state)});
                
                // Redirect to OAuth server
                window.location.href = {json.dumps(auth_url)};
            </script>
            <p>Redirecting to SVA...</p>
        </body>
        </html>
        """
        return HttpResponse(html)
        
    except Exception as e:
        logger.error(f"Error in oauth_login: {str(e)}", exc_info=True)
        return redirect(getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/'))

@require_http_methods(["GET"])
def oauth_callback(request):
    """
    Handle OAuth callback - Validate signed state, then exchange token.
    """
    error = request.GET.get('error')
    if error:
        error_desc = request.GET.get('error_description', error)
        return render_error(f"OAuth Error: {error_desc}")
    
    code = request.GET.get('code')
    signed_state = request.GET.get('state')
    
    if not code or not signed_state:
        return render_error("Missing authorization code or state parameter.")
    
    # CRITICAL: Validate the signed state.
    try:
        # max_age=600 ensures the link expires after 10 minutes
        original_token = signing.loads(signed_state, max_age=600)
        logger.info("State signature verified successfully (Stateless).")
    except signing.SignatureExpired:
        logger.warning("OAuth login attempt expired.")
        return render_error("Login attempt expired. Please try again.")
    except signing.BadSignature:
        logger.error("Invalid state signature! Potential tampering.")
        return render_error("Security check failed. Invalid state parameter.")
    
    # render the client-side exchange page
    success_url = getattr(settings, 'SVA_OAUTH_SUCCESS_REDIRECT', '/dashboard/')
    error_url = getattr(settings, 'SVA_OAUTH_ERROR_REDIRECT', '/')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Completing Authentication...</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, sans-serif;
                text-align: center;
                padding: 40px;
                color: #333;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .success-message {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                max-width: 400px;
                width: 90%;
            }}
            .icon {{ font-size: 48px; margin-bottom: 20px; }}
            h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
            p {{ color: #666; margin-bottom: 30px; }}
            .btn {{
                background: #00D09C; color: white; border: none; padding: 12px 24px;
                border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: 500;
                text-decoration: none; display: inline-block;
            }}
            .btn:hover {{ opacity: 0.9; }}
        </style>
    </head>
    <body>
        <p id="status">Completing authentication...</p>
        <script>
            const code = {json.dumps(code)};
            const state = {json.dumps(signed_state)};
            const codeVerifier = localStorage.getItem('sva_oauth_code_verifier');
            const successUrl = {json.dumps(success_url)};
            const errorUrl = {json.dumps(error_url)};
            
            if (!codeVerifier) {{
                alert('Browser session lost (missing code verifier). Please try again.');
                window.location.href = errorUrl;
            }} else {{
                fetch('/oauth/exchange/', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken') || ''
                    }},
                    body: JSON.stringify({{ code: code, state: state, code_verifier: codeVerifier }})
                }})
                .then(r => r.json())
                .then(data => {{
                    localStorage.removeItem('sva_oauth_code_verifier');
                    localStorage.removeItem('sva_oauth_state');
                    
                    if (data.success) {{
                        const isPopupByName = window.name === 'sva_login_popup';
                        const hasOpener = window.opener && window.opener !== window;
                        // Fallback: If window is small, assume it's a popup
                        const isSmallWindow = window.innerWidth < 800 && window.innerHeight < 900;
                        
                        // DECISION LOGIC
                        if (hasOpener) {{
                            // Ideally, notify parent and close
                            try {{
                                window.opener.postMessage('sva_login_success', '*');
                                window.close();
                            }} catch (e) {{
                                console.error("Failed to post message to opener:", e);
                                showSuccessUI();
                            }}
                        }} else if (isPopupByName || isSmallWindow) {{
                            // Orphaned popup or small window - DO NOT REDIRECT
                            showSuccessUI();
                        }} else {{
                            // Main window - Redirect
                            window.location.href = successUrl;
                        }}
                    }} else {{
                        alert('Login failed: ' + (data.error || 'Unknown error'));
                        window.location.href = errorUrl;
                    }}
                }})
                .catch(e => {{
                    console.error(e);
                    alert('Login error.');
                    window.location.href = errorUrl;
                }});
            }}
            
            function showSuccessUI() {{
                document.body.innerHTML = `
                    <div class="success-message">
                        <div class="icon">✅</div>
                        <h1>Sign in successful</h1>
                        <p>You can now close this window.</p>
                        <button onclick="window.close()" class="btn">Close Window</button>
                        <br><br>
                        <a href="${{successUrl}}" target="_blank" style="color: #666; font-size: 12px;">Go to Dashboard</a>
                    </div>
                `;
            }}
            
            function getCookie(name) {{
                if (!document.cookie) return null;
                const value = `; ${{document.cookie}}`;
                const parts = value.split(`; ${{name}}=`);
                if (parts.length === 2) return parts.pop().split(';').shift();
            }}
        </script>
    </body>
    </html>
    """
    return HttpResponse(html)

def render_error(msg):
    return HttpResponse(f"<html><body><h1>Login Failed</h1><p>{msg}</p><a href='/'>Go Home</a></body></html>")

@csrf_exempt
@require_http_methods(["POST"])
def oauth_exchange(request):
    """
    Exchange code for tokens.
    """
    try:
        data = json.loads(request.body)
        code = data.get('code')
        state = data.get('state')
        code_verifier = data.get('code_verifier')
        
        client = get_client_from_settings()
        token_response = client.exchange_code_for_tokens(code=code, code_verifier=code_verifier, state=state)
        
        request.session['sva_oauth_access_token'] = token_response.get('access_token')
        request.session['sva_oauth_refresh_token'] = token_response.get('refresh_token')
        request.session['sva_oauth_data_token'] = token_response.get('data_token', '')
        request.session['sva_oauth_scope'] = token_response.get('scope', '')
        
        request.session.modified = True
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Exchange error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["GET", "POST"])
def oauth_logout(request):
    clear_oauth_session(request.session)
    return redirect(getattr(settings, 'SVA_OAUTH_LOGOUT_REDIRECT', '/'))

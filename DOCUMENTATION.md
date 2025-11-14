# sva-oauth-client API Documentation

## Introduction

`sva-oauth-client` is the official Python/Django integration package for the Sva Identity Protocol. It provides a secure, simple, and stateless way to add "Continue with Sva" authentication to any Django application. The package handles the complete OAuth 2.0 flow with PKCE (Proof Key for Code Exchange) and delivers user identity claims directly in a cryptographically signed JWT, eliminating the need for inefficient API calls to a `/userinfo` endpoint.

## Installation

Install the package using pip:

```bash
pip install sva-oauth-client
```

## Quick Start

Get up and running in 5 minutes with these simple steps:

### 1. Add to INSTALLED_APPS

In your Django `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    'sva_oauth_client',
]
```

### 2. Add to MIDDLEWARE

Add the token refresh middleware to your `MIDDLEWARE` list:

```python
MIDDLEWARE = [
    # ... other middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... other middleware
    'sva_oauth_client.middleware.TokenRefreshMiddleware',
]
```

**Important:** The `TokenRefreshMiddleware` must come after `SessionMiddleware` since it requires access to the session.

### 3. Configure Settings

Add the required settings to your `settings.py`:

```python
# Required Settings
SVA_OAUTH_BASE_URL = 'https://your-sva-provider.com'  # Your SVA OAuth provider URL
SVA_OAUTH_CLIENT_ID = 'your_client_id_here'
SVA_OAUTH_CLIENT_SECRET = 'your_client_secret_here'
SVA_OAUTH_REDIRECT_URI = 'https://your-app.com/oauth/callback/'
SVA_DATA_TOKEN_SECRET = 'your_data_token_secret'  # Must match your SVA provider
```

### 4. Add URLs

Include the OAuth URLs in your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... your other URLs
    path('oauth/', include('sva_oauth_client.urls')),
]
```

This will automatically provide the following endpoints:
- `/oauth/login/` - Initiate OAuth flow
- `/oauth/callback/` - OAuth callback handler
- `/oauth/exchange/` - Token exchange endpoint
- `/oauth/logout/` - Logout endpoint

### 5. Create a Protected View

Create a simple view that uses the decorator and utility function:

```python
from django.shortcuts import render
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_sva_claims

@sva_oauth_required
def dashboard(request):
    # Get user claims directly from the signed data_token (stateless!)
    claims = get_sva_claims(request)
    
    context = {
        'email': claims.get('email'),
        'name': claims.get('name'),
        'all_claims': claims,
    }
    return render(request, 'dashboard.html', context)
```

That's it! Your Django app now has secure, stateless OAuth authentication with Sva.

## Configuration

### Required Settings

| Setting | Description | Example |
|---------|-------------|---------|
| `SVA_OAUTH_BASE_URL` | Base URL of your SVA OAuth provider. This is the root URL where your SVA provider is hosted. | `'https://sva-provider.com'` |
| `SVA_OAUTH_CLIENT_ID` | Your OAuth client ID. Obtain this from your SVA OAuth provider when you register your application. | `'app_abc123xyz'` |
| `SVA_OAUTH_CLIENT_SECRET` | Your OAuth client secret. **Keep this secure!** Never commit it to version control. | `'secret_key_here'` |
| `SVA_OAUTH_REDIRECT_URI` | The redirect URI registered in your OAuth app. Must match exactly (including protocol, domain, port, and path). | `'https://yourapp.com/oauth/callback/'` |
| `SVA_DATA_TOKEN_SECRET` | Secret key used to verify the signature of the data_token JWT. **Must match** the secret configured in your SVA provider. | `'your_data_token_secret'` |

### Optional Settings

| Setting | Description | Default | Example |
|---------|-------------|---------|---------|
| `SVA_DATA_TOKEN_ALGORITHM` | JWT algorithm used for data_token verification. | `'HS256'` | `'HS256'` or `'RS256'` |
| `SVA_OAUTH_SCOPES` | Space-separated list of scopes (identity blocks) to request. | `'openid email profile'` | `'openid email profile username name'` |
| `SVA_OAUTH_SUCCESS_REDIRECT` | URL to redirect to after successful authentication. | `'/dashboard/'` | `'/'` or `'/home/'` |
| `SVA_OAUTH_ERROR_REDIRECT` | URL to redirect to on authentication errors. | `'/'` | `'/error/'` |
| `SVA_OAUTH_LOGOUT_REDIRECT` | URL to redirect to after logout. | `'/'` | `'/login/'` |
| `SVA_OAUTH_LOGIN_URL` | The login URL path used by decorators for redirects. | `'/oauth/login/'` | `'/auth/login/'` |

## Core Components (API Reference)

### Views (`views.py`)

The package provides four views that work together automatically to handle the complete OAuth flow:

#### `/oauth/login/` - OAuth Login Initiation

**Purpose:** Initiates the OAuth flow by generating PKCE parameters and redirecting the user to the SVA provider's authorization page.

**How it works:**
1. Generates a secure state parameter for CSRF protection
2. Generates a code verifier and challenge for PKCE
3. Stores PKCE data temporarily in localStorage (via JavaScript)
4. Redirects the user to the SVA provider's authorization endpoint

**Usage:** Users navigate to this URL or you can link to it from your login page:

```html
<a href="{% url 'sva_oauth_client:login' %}">Continue with Sva</a>
```

#### `/oauth/callback/` - OAuth Callback Handler

**Purpose:** Handles the OAuth callback from the SVA provider after user authorization.

**How it works:**
1. Receives the authorization code and state from the SVA provider
2. Validates the state parameter for CSRF protection
3. Retrieves the code verifier from localStorage
4. Exchanges the authorization code for tokens via `/oauth/exchange/`
5. Stores tokens in the session and redirects to the success URL

**Usage:** This endpoint is called automatically by the SVA provider. You must register this exact URL in your OAuth app configuration.

#### `/oauth/exchange/` - Token Exchange Endpoint

**Purpose:** Exchanges the authorization code for access tokens and the data_token.

**How it works:**
1. Receives authorization code, state, and code verifier from the callback page
2. Exchanges code for tokens using PKCE verification
3. Stores access token, refresh token, and data_token in the session
4. Handles "Remember Me" functionality by setting session expiry
5. Returns success/error response to the callback page

**Usage:** This is an internal endpoint called by JavaScript from the callback page. You typically don't need to interact with it directly.

#### `/oauth/logout/` - Logout Endpoint

**Purpose:** Clears all OAuth-related session data and logs the user out.

**Usage:**

```python
from django.shortcuts import redirect
from sva_oauth_client.views import oauth_logout

def my_logout_view(request):
    return oauth_logout(request)
```

Or link to it directly:

```html
<a href="{% url 'sva_oauth_client:logout' %}">Logout</a>
```

### Decorators (`decorators.py`)

#### `@sva_oauth_required`

**Purpose:** The primary decorator to protect views that require authentication. Redirects unauthenticated users to the login page.

**Usage:**

```python
from sva_oauth_client.decorators import sva_oauth_required

@sva_oauth_required
def protected_view(request):
    # User is guaranteed to be authenticated here
    claims = get_sva_claims(request)
    return render(request, 'protected.html', {'claims': claims})
```

**Behavior:**
- Checks if the user has a valid access token in their session
- If not authenticated, redirects to `SVA_OAUTH_LOGIN_URL` (default: `/oauth/login/`)
- Displays an info message prompting the user to sign in

#### `@sva_blocks_required(*claims)`

**Purpose:** Decorator to require specific identity claims (blocks) to be present in the data_token. Useful for views that need specific user information.

**Parameters:**
- `*claims`: Variable number of claim names that must be present

**Usage:**

```python
from sva_oauth_client.decorators import sva_blocks_required

@sva_blocks_required('email', 'name', 'phone')
def profile_view(request):
    # User is authenticated AND has email, name, and phone claims
    claims = get_sva_claims(request)
    email = claims['email']  # Guaranteed to exist
    name = claims['name']     # Guaranteed to exist
    phone = claims['phone']  # Guaranteed to exist
    return render(request, 'profile.html', {'email': email, 'name': name, 'phone': phone})
```

**Behavior:**
- First checks if the user is authenticated (same as `@sva_oauth_required`)
- Verifies that the data_token is valid and not expired
- Checks that all required claims are present in the data_token
- If any claim is missing, redirects to login with an error message
- If the token is invalid or expired, triggers logout and redirects to login

**Error Handling:**
- Automatically handles `SVATokenError` exceptions (expired/invalid tokens)
- Displays appropriate error messages to guide the user

### Middleware (`middleware.py`)

#### `TokenRefreshMiddleware`

**Purpose:** Automatically refreshes access tokens before they expire, providing a seamless user experience without requiring re-authentication.

**How it works:**
1. Checks each request for an access token in the session
2. Verifies if the token is close to expiring (within 60 seconds)
3. Silently refreshes the token using the refresh token
4. Updates the session with new tokens and expiry time
5. Handles refresh failures gracefully by logging out the user

**Configuration:**

Simply add it to your `MIDDLEWARE` list (after `SessionMiddleware`):

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # ... other middleware
    'sva_oauth_client.middleware.TokenRefreshMiddleware',
]
```

**Important Notes:**
- The middleware runs automatically on every request - no additional configuration needed
- Token refresh is silent and transparent to the user
- If refresh fails (e.g., refresh token expired), the user is automatically logged out
- The middleware preserves "Remember Me" session settings

### Utility Functions (`utils.py`)

#### `get_sva_claims(request)`

**Purpose:** The primary method for accessing user identity data. Retrieves and decodes SVA claims from the cryptographically signed data_token stored in the session.

**Parameters:**
- `request`: Django `HttpRequest` object (must have session attribute)

**Returns:**
- `Dict[str, Any]`: Dictionary containing all identity claims (blocks), or `None` if no data_token is present

**Raises:**
- `SVATokenError`: If the data_token is invalid, expired, or has a bad signature

**Usage:**

```python
from sva_oauth_client.utils import get_sva_claims
from sva_oauth_client.client import SVATokenError

@sva_oauth_required
def my_view(request):
    try:
        claims = get_sva_claims(request)
        if claims:
            email = claims.get('email')
            name = claims.get('name')
            phone = claims.get('phone')
            # Use claims directly - no API call needed!
    except SVATokenError:
        # Token expired or invalid - user will be logged out
        return redirect('login')
```

**Claims Dictionary Structure:**

The claims dictionary contains all identity blocks that the user approved during the consent screen. Common claims include:

```python
{
    'email': 'user@example.com',
    'name': 'John Doe',
    'phone': '+1234567890',
    'username': 'johndoe',
    'bio': 'Software developer',
    'address': {
        'street': '123 Main St',
        'city': 'New York',
        'zip': '10001'
    },
    'social': {
        'twitter': '@johndoe',
        'github': 'johndoe'
    },
    # ... other approved identity blocks
}
```

**Important Notes:**
- This function is **stateless** - it decodes the JWT directly from the session
- No API call to `/userinfo` is made - all data comes from the signed token
- The token signature and expiration are automatically verified
- If the token is invalid or expired, `SVATokenError` is raised

#### `is_authenticated(session)`

**Purpose:** Check if a user is authenticated with SVA OAuth by verifying the presence of an access token.

**Parameters:**
- `session`: Django session object

**Returns:**
- `bool`: `True` if authenticated, `False` otherwise

**Usage:**

```python
from sva_oauth_client.utils import is_authenticated

def my_view(request):
    if is_authenticated(request.session):
        # User is logged in
        return render(request, 'dashboard.html')
    else:
        # User is not logged in
        return render(request, 'login.html')
```

**Template Usage:**

You can also use this in templates for conditional rendering:

```python
# In your view
context = {'is_authenticated': is_authenticated(request.session)}
```

```django
{% if is_authenticated %}
    <a href="{% url 'sva_oauth_client:logout' %}">Logout</a>
{% else %}
    <a href="{% url 'sva_oauth_client:login' %}">Login</a>
{% endif %}
```

#### Other Utility Functions

The package also provides these utility functions for advanced use cases:

- `get_access_token(session)`: Get the access token from session
- `get_data_token(session)`: Get the raw data_token string from session
- `clear_oauth_session(session)`: Clear all OAuth-related session data
- `get_client_from_settings()`: Get a configured `SVAOAuthClient` instance

## Advanced Usage

### "Remember Me" Functionality

The package supports "Remember Me" functionality to extend session persistence. Here's how to implement it:

#### Frontend: Add Checkbox to Login Form

```html
<form method="post" action="{% url 'sva_oauth_client:login' %}">
    {% csrf_token %}
    <label>
        <input type="checkbox" name="remember_me" value="true">
        Remember me for 30 days
    </label>
    <button type="submit">Continue with Sva</button>
</form>
```

#### Backend: Automatic Handling

The package automatically handles "Remember Me" when the login form is submitted via POST:

1. The `remember_me` preference is stored in the session during login initiation
2. When tokens are exchanged, the session expiry is set based on the preference:
   - **Remember Me enabled:** Session expires in 30 days
   - **Remember Me disabled:** Session expires when browser closes (default secure behavior)

**Security Note:** The "Remember Me" functionality uses Django's secure session framework with HttpOnly cookies, ensuring the session cannot be accessed via JavaScript.

### Error Handling

The package defines custom exceptions for better error handling:

#### `SVAOAuthError`

Base exception for all SVA OAuth errors.

#### `SVATokenError`

Raised when token operations fail (invalid token, expired token, bad signature, etc.).

**Usage:**

```python
from sva_oauth_client.client import SVATokenError
from sva_oauth_client.utils import get_sva_claims

@sva_oauth_required
def my_view(request):
    try:
        claims = get_sva_claims(request)
        # Process claims...
    except SVATokenError as e:
        # Token is invalid or expired
        # The decorator or middleware will handle logout
        messages.error(request, 'Your session has expired. Please sign in again.')
        return redirect('login')
```

**Automatic Handling:**

- The `@sva_blocks_required` decorator automatically catches `SVATokenError` and redirects to login
- The `TokenRefreshMiddleware` handles token refresh failures by logging out the user
- You can catch `SVATokenError` in your views for custom error handling

## Security Model

### Security Features

The `sva-oauth-client` package implements multiple layers of security:

1. **PKCE (Proof Key for Code Exchange):** Prevents authorization code interception attacks by using a code verifier and challenge
2. **HttpOnly Server-Side Sessions:** All tokens are stored in server-side sessions with HttpOnly cookies, preventing XSS attacks
3. **State Parameter for CSRF Protection:** Each OAuth flow includes a unique state parameter to prevent CSRF attacks
4. **JWT Signature Verification:** The data_token is cryptographically signed and verified on every request to ensure integrity
5. **Automatic Token Expiration:** Tokens have expiration times and are automatically refreshed before expiry

### Why We Don't Use a `/userinfo` Endpoint

**Our Stateless Philosophy:**

The `sva-oauth-client` package is designed around a stateless architecture that eliminates the need for a separate `/userinfo` endpoint. Here's why this approach is superior:

#### Performance Benefits

- **Zero Network Overhead:** User identity data is delivered directly in the `data_token` JWT during token exchange. No additional HTTP requests are needed to fetch user information.
- **Reduced Latency:** Every request that needs user data would otherwise require a round-trip to the OAuth provider's `/userinfo` endpoint. With our approach, data is decoded locally from the session.
- **Better Scalability:** Your application doesn't need to make external API calls on every request, reducing load on both your server and the OAuth provider.

#### Security Benefits

- **Cryptographic Integrity:** The `data_token` is cryptographically signed by the OAuth provider. Any tampering with the data is immediately detected through signature verification.
- **Reduced Attack Surface:** Fewer network requests mean fewer opportunities for man-in-the-middle attacks or token interception.
- **Self-Contained:** All user data is contained within the signed token, making it impossible for the data to be modified without detection.

#### Developer Experience

- **Simpler Code:** No need to handle API calls, retries, or error handling for `/userinfo` requests.
- **Consistent Data:** The data_token contains a snapshot of user data at the time of consent, ensuring consistency across requests.
- **Offline Capability:** Once the token is received, your application can access user data even if the OAuth provider is temporarily unavailable.

#### How It Works

1. **During Token Exchange:** The OAuth provider includes a `data_token` JWT in the token response. This token contains all approved identity claims (blocks) in its payload.

2. **Token Storage:** The `data_token` is stored in the user's session (server-side, HttpOnly cookie).

3. **On Each Request:** When you call `get_sva_claims(request)`, the function:
   - Retrieves the `data_token` from the session
   - Verifies the cryptographic signature using `SVA_DATA_TOKEN_SECRET`
   - Verifies the token hasn't expired
   - Extracts and returns the claims dictionary

4. **No API Calls:** The entire process happens locally - no network requests to `/userinfo` are ever made.

This stateless design provides the best performance, security, and developer experience while maintaining the cryptographic guarantees you need for user identity data.

---

## Additional Resources

- **Package Repository:** [GitHub Repository URL]
- **SVA Identity Protocol Documentation:** [Protocol Documentation URL]
- **Support:** [Support Contact Information]

---

*Last Updated: [Current Date]*


# SVA OAuth Client

A professional Django package for integrating SVA (Secure Vault Authentication) OAuth provider into your Django applications. This package provides a complete solution for authenticating users via SVA OAuth and retrieving identity blocks data from the consent screen.

## Features

- ✅ **Complete OAuth 2.0 Flow**: Authorization Code Flow with PKCE support
- ✅ **Easy Integration**: Simple decorators and utilities for quick setup
- ✅ **Identity Blocks**: Retrieve all blocks data from consent screen
- ✅ **Session Management**: Automatic token storage and management
- ✅ **Error Handling**: Comprehensive error handling with user-friendly messages
- ✅ **Django Integration**: Seamless integration with Django views and templates
- ✅ **Type Hints**: Full type hint support for better IDE experience

## Installation

```bash
pip install sva-oauth-client
```

Or install from source:

```bash
git clone https://github.com/getsva/sva-oauth-client.git
cd sva-oauth-client
pip install -e .
```

## Quick Start

### 1. Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'sva_oauth_client',
]
```

### 2. Configure Settings

```python
# settings.py

# SVA OAuth Configuration
SVA_OAUTH_BASE_URL = 'http://localhost:8000'  # Your SVA OAuth provider URL
SVA_OAUTH_CLIENT_ID = 'your_client_id_here'
SVA_OAUTH_CLIENT_SECRET = 'your_client_secret_here'
SVA_OAUTH_REDIRECT_URI = 'http://localhost:8001/oauth/callback/'
SVA_DATA_TOKEN_SECRET = 'your_data_token_secret'  # Must match SVA provider
SVA_DATA_TOKEN_ALGORITHM = 'HS256'  # Default: HS256

# Optional: Request specific scopes (default: 'openid email profile')
SVA_OAUTH_SCOPES = 'openid email profile username name bio address social images pronoun dob skills hobby email phone pan_card crypto_wallet education employment professional_license aadhar driving_license voter_id passport'

# Optional: Custom redirect URLs
SVA_OAUTH_SUCCESS_REDIRECT = '/'  # After successful login
SVA_OAUTH_ERROR_REDIRECT = '/'   # On error
SVA_OAUTH_LOGOUT_REDIRECT = '/'  # After logout
SVA_OAUTH_LOGIN_URL = '/oauth/login/'  # Login URL
```

### 3. Add URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ... other URLs
    path('oauth/', include('sva_oauth_client.urls')),
]
```

### 4. Use in Your Views

#### Basic Usage

```python
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data, get_userinfo

@sva_oauth_required
def my_view(request):
    # User is authenticated with SVA OAuth
    blocks_data = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    return render(request, 'my_template.html', {
        'blocks': blocks_data,
        'userinfo': userinfo,
    })
```

#### Require Specific Blocks

```python
from sva_oauth_client.decorators import sva_blocks_required
from sva_oauth_client.utils import get_blocks_data

@sva_blocks_required('email', 'name', 'phone')
def my_view(request):
    # User has approved email, name, and phone blocks
    blocks_data = get_blocks_data(request.session)
    
    email = blocks_data.get('email')
    name = blocks_data.get('name')
    phone = blocks_data.get('phone')
    
    return render(request, 'my_template.html', {
        'email': email,
        'name': name,
        'phone': phone,
    })
```

#### Manual Client Usage

```python
from sva_oauth_client import SVAOAuthClient

# Initialize client
client = SVAOAuthClient(
    base_url='http://localhost:8000',
    client_id='your_client_id',
    client_secret='your_client_secret',
    redirect_uri='http://localhost:8001/oauth/callback/',
    data_token_secret='your_data_token_secret',
)

# Get authorization URL
auth_url, code_verifier = client.get_authorization_url()
# Store code_verifier in session
request.session['code_verifier'] = code_verifier
# Redirect user to auth_url

# After callback, exchange code for tokens
tokens = client.exchange_code_for_tokens(
    code=request.GET.get('code'),
    code_verifier=request.session.get('code_verifier')
)

# Get blocks data
blocks_data = client.get_blocks_data(tokens['data_token'])
```

## API Reference

### SVAOAuthClient

Main OAuth client class.

#### Methods

- `get_authorization_url(state=None, code_verifier=None) -> tuple[str, str]`
  - Generate authorization URL and code verifier
  - Returns: (authorization_url, code_verifier)

- `exchange_code_for_tokens(code, code_verifier, state=None) -> dict`
  - Exchange authorization code for tokens
  - Returns: Dictionary with access_token, refresh_token, data_token, etc.

- `refresh_access_token(refresh_token) -> dict`
  - Refresh access token using refresh token

- `get_userinfo(access_token) -> dict`
  - Get user information from OAuth provider

- `decode_data_token(data_token) -> dict`
  - Decode and verify data_token JWT

- `get_blocks_data(data_token) -> dict`
  - Extract blocks data from data_token

### Decorators

#### `@sva_oauth_required`

Require SVA OAuth authentication. Redirects to login if not authenticated.

```python
@sva_oauth_required
def my_view(request):
    # User is authenticated
    pass
```

#### `@sva_blocks_required(*blocks)`

Require specific identity blocks. Redirects to login if blocks are missing.

```python
@sva_blocks_required('email', 'name', 'phone')
def my_view(request):
    # User has approved email, name, and phone
    pass
```

### Utility Functions

#### `get_blocks_data(session) -> dict | None`

Get blocks data from session.

#### `get_userinfo(session) -> dict | None`

Get userinfo from session or fetch from OAuth provider.

#### `get_access_token(session) -> str | None`

Get access token from session.

#### `get_data_token(session) -> str | None`

Get data token from session.

#### `is_authenticated(session) -> bool`

Check if user is authenticated with SVA OAuth.

#### `clear_oauth_session(session) -> None`

Clear all OAuth-related data from session.

## Identity Blocks

The package supports all SVA identity blocks:

### Core Identity
- `username` - Username
- `name` - Full name
- `bio` - Bio/description
- `pronoun` - Pronouns
- `dob` - Date of birth

### Profile Information
- `images` - Profile images
- `skills` - Skills
- `hobby` - Hobbies

### Contact Information
- `address` - Address
- `social` - Social links

### Verified Identity Blocks
- `email` - Verified email
- `phone` - Verified phone
- `pan_card` - PAN card
- `crypto_wallet` - Crypto wallet
- `education` - Education
- `employment` - Employment
- `professional_license` - Professional license
- `aadhar` - Aadhaar card
- `driving_license` - Driving license
- `voter_id` - Voter ID
- `passport` - Passport

## Examples

### Complete Example

```python
# views.py
from django.shortcuts import render
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data, get_userinfo

@sva_oauth_required
def dashboard(request):
    blocks_data = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    context = {
        'blocks': blocks_data,
        'userinfo': userinfo,
        'email': blocks_data.get('email') if blocks_data else None,
        'name': blocks_data.get('name') if blocks_data else None,
    }
    
    return render(request, 'dashboard.html', context)
```

### Template Example

```django
<!-- dashboard.html -->
<h1>Welcome!</h1>

{% if blocks %}
    <h2>Your Identity Blocks</h2>
    <ul>
        {% for key, value in blocks.items %}
            <li><strong>{{ key }}:</strong> {{ value }}</li>
        {% endfor %}
    </ul>
{% endif %}

{% if userinfo %}
    <h2>User Information</h2>
    <p>Subject: {{ userinfo.sub }}</p>
    <p>Email: {{ userinfo.email }}</p>
{% endif %}
```

## Error Handling

The package provides comprehensive error handling:

```python
from sva_oauth_client.client import SVAOAuthClient, SVATokenError, SVAAuthorizationError

try:
    client = SVAOAuthClient(...)
    tokens = client.exchange_code_for_tokens(code, code_verifier)
except SVATokenError as e:
    # Handle token errors
    print(f"Token error: {e}")
except SVAAuthorizationError as e:
    # Handle authorization errors
    print(f"Authorization error: {e}")
```

## Security Best Practices

1. **Never expose secrets**: Keep `SVA_OAUTH_CLIENT_SECRET` and `SVA_DATA_TOKEN_SECRET` secure
2. **Use HTTPS in production**: Always use HTTPS for OAuth redirects in production
3. **Validate state parameter**: The package automatically validates state for CSRF protection
4. **Store tokens securely**: Tokens are stored in Django session (server-side)
5. **Handle token expiration**: Implement token refresh logic for long-lived sessions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/getsva/sva-oauth-client/issues
- Email: support@getsva.com


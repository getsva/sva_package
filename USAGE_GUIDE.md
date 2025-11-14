# Complete Usage Guide

## Table of Contents

1. [Installation](#installation)
2. [Basic Setup](#basic-setup)
3. [Simple Usage](#simple-usage)
4. [Advanced Usage](#advanced-usage)
5. [API Reference](#api-reference)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Installation

```bash
pip install sva-oauth-client
```

## Basic Setup

### Step 1: Django Settings

```python
# settings.py
INSTALLED_APPS = [
    # ... other apps
    'sva_oauth_client',
]

# Required settings
SVA_OAUTH_BASE_URL = 'http://localhost:8000'
SVA_OAUTH_CLIENT_ID = 'your_client_id'
SVA_OAUTH_CLIENT_SECRET = 'your_client_secret'
SVA_OAUTH_REDIRECT_URI = 'http://localhost:8001/oauth/callback/'
SVA_DATA_TOKEN_SECRET = 'your_data_token_secret'
```

### Step 2: URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('oauth/', include('sva_oauth_client.urls')),
]
```

## Simple Usage

### Example 1: Protected View

```python
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data

@sva_oauth_required
def dashboard(request):
    blocks = get_blocks_data(request.session)
    return render(request, 'dashboard.html', {'blocks': blocks})
```

### Example 2: Require Specific Blocks

```python
@sva_blocks_required('email', 'name', 'phone')
def profile(request):
    blocks = get_blocks_data(request.session)
    return render(request, 'profile.html', {'blocks': blocks})
```

### Example 3: Login Link

```django
<a href="{% url 'sva_oauth_client:login' %}">Sign In with SVA</a>
```

## Advanced Usage

### Manual Client Usage

```python
from sva_oauth_client import SVAOAuthClient

client = SVAOAuthClient(
    base_url='http://localhost:8000',
    client_id='your_client_id',
    client_secret='your_client_secret',
    redirect_uri='http://localhost:8001/oauth/callback/',
    data_token_secret='your_data_token_secret',
)

# Get authorization URL
auth_url, code_verifier = client.get_authorization_url()
request.session['code_verifier'] = code_verifier
return redirect(auth_url)
```

### Token Refresh

```python
from sva_oauth_client.utils import get_client_from_settings

client = get_client_from_settings()
refresh_token = request.session.get('sva_oauth_refresh_token')
new_tokens = client.refresh_access_token(refresh_token)
```

### Error Handling

```python
from sva_oauth_client.client import SVATokenError, SVAAuthorizationError

try:
    tokens = client.exchange_code_for_tokens(code, code_verifier)
except SVATokenError as e:
    # Handle token errors
    messages.error(request, f"Token error: {e}")
except SVAAuthorizationError as e:
    # Handle authorization errors
    messages.error(request, f"Authorization error: {e}")
```

## API Reference

### SVAOAuthClient

#### Methods

- `get_authorization_url(state=None, code_verifier=None) -> tuple`
- `exchange_code_for_tokens(code, code_verifier, state=None) -> dict`
- `refresh_access_token(refresh_token) -> dict`
- `get_userinfo(access_token) -> dict`
- `decode_data_token(data_token) -> dict`
- `get_blocks_data(data_token) -> dict`

### Decorators

- `@sva_oauth_required` - Require authentication
- `@sva_blocks_required(*blocks)` - Require specific blocks

### Utilities

- `get_blocks_data(session)` - Get blocks from session
- `get_userinfo(session)` - Get userinfo from session
- `is_authenticated(session)` - Check authentication
- `clear_oauth_session(session)` - Clear OAuth data

## Best Practices

1. **Use Environment Variables**: Store secrets in environment variables
2. **HTTPS in Production**: Always use HTTPS for OAuth redirects
3. **Error Handling**: Always handle exceptions properly
4. **Token Refresh**: Implement token refresh for long sessions
5. **Session Security**: Use secure session settings in production

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure package is installed
2. **Settings Error**: Verify all required settings are set
3. **OAuth Error**: Check client ID, secret, and redirect URI
4. **Token Error**: Verify data token secret matches provider

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('sva_oauth_client').setLevel(logging.DEBUG)
```

## Complete Example

```python
# views.py
from django.shortcuts import render, redirect
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data, get_userinfo

@sva_oauth_required
def dashboard(request):
    blocks = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    context = {
        'blocks': blocks or {},
        'userinfo': userinfo or {},
        'email': blocks.get('email') if blocks else None,
        'name': blocks.get('name') if blocks else None,
    }
    
    return render(request, 'dashboard.html', context)
```

```django
<!-- dashboard.html -->
<h1>Dashboard</h1>

{% if blocks %}
    <h2>Identity Blocks</h2>
    <ul>
        {% for key, value in blocks.items %}
            <li><strong>{{ key }}:</strong> {{ value }}</li>
        {% endfor %}
    </ul>
{% endif %}

<a href="{% url 'sva_oauth_client:logout' %}">Logout</a>
```


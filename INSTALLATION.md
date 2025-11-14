# Installation Guide

## Prerequisites

- Python 3.8 or higher
- Django 3.2 or higher
- An SVA OAuth provider instance running
- An OAuth app registered in your SVA OAuth provider

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
pip install sva-oauth-client
```

### Method 2: Install from Source

```bash
git clone https://github.com/getsva/sva-oauth-client.git
cd sva-oauth-client
pip install -e .
```

### Method 3: Install from Local Directory

```bash
cd /path/to/sva-oauth-client
pip install -e .
```

## Django Project Setup

### Step 1: Add to INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Add sva_oauth_client
    'sva_oauth_client',
    
    # Your apps
    # ...
]
```

### Step 2: Configure Settings

Add the following to your `settings.py`:

```python
# SVA OAuth Configuration
SVA_OAUTH_BASE_URL = 'http://localhost:8000'  # Your SVA OAuth provider URL
SVA_OAUTH_CLIENT_ID = 'your_client_id_here'
SVA_OAUTH_CLIENT_SECRET = 'your_client_secret_here'
SVA_OAUTH_REDIRECT_URI = 'http://localhost:8001/oauth/callback/'
SVA_DATA_TOKEN_SECRET = 'your_data_token_secret'  # Must match SVA provider
SVA_DATA_TOKEN_ALGORITHM = 'HS256'  # Default: HS256

# Optional: Request specific scopes
SVA_OAUTH_SCOPES = 'openid email profile username name bio address social images pronoun dob skills hobby email phone pan_card crypto_wallet education employment professional_license aadhar driving_license voter_id passport'

# Optional: Custom redirect URLs
SVA_OAUTH_SUCCESS_REDIRECT = '/'  # After successful login
SVA_OAUTH_ERROR_REDIRECT = '/'   # On error
SVA_OAUTH_LOGOUT_REDIRECT = '/'  # After logout
SVA_OAUTH_LOGIN_URL = '/oauth/login/'  # Login URL
```

### Step 3: Add URLs

```python
# urls.py (project-level)
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('oauth/', include('sva_oauth_client.urls')),  # Add this
    # ... your other URLs
]
```

### Step 4: Run Migrations

```bash
python manage.py migrate
```

### Step 5: Create Your First View

```python
# views.py
from django.shortcuts import render
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data, get_userinfo

@sva_oauth_required
def dashboard(request):
    blocks_data = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    return render(request, 'dashboard.html', {
        'blocks': blocks_data,
        'userinfo': userinfo,
    })
```

### Step 6: Create Template

```django
<!-- templates/dashboard.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <h1>Welcome!</h1>
    
    {% if blocks %}
        <h2>Your Identity Blocks</h2>
        <ul>
            {% for key, value in blocks.items %}
                <li><strong>{{ key }}:</strong> {{ value }}</li>
            {% endfor %}
        </ul>
    {% endif %}
    
    <a href="{% url 'sva_oauth_client:logout' %}">Logout</a>
</body>
</html>
```

## Environment Variables (Recommended)

For production, use environment variables:

```python
# settings.py
import os

SVA_OAUTH_BASE_URL = os.getenv('SVA_OAUTH_BASE_URL', 'http://localhost:8000')
SVA_OAUTH_CLIENT_ID = os.getenv('SVA_OAUTH_CLIENT_ID', '')
SVA_OAUTH_CLIENT_SECRET = os.getenv('SVA_OAUTH_CLIENT_SECRET', '')
SVA_OAUTH_REDIRECT_URI = os.getenv('SVA_OAUTH_REDIRECT_URI', '')
SVA_DATA_TOKEN_SECRET = os.getenv('SVA_DATA_TOKEN_SECRET', '')
```

Then create a `.env` file:

```bash
SVA_OAUTH_BASE_URL=http://localhost:8000
SVA_OAUTH_CLIENT_ID=your_client_id
SVA_OAUTH_CLIENT_SECRET=your_client_secret
SVA_OAUTH_REDIRECT_URI=http://localhost:8001/oauth/callback/
SVA_DATA_TOKEN_SECRET=your_data_token_secret
```

## Testing the Installation

1. Start your Django development server:
   ```bash
   python manage.py runserver 8001
   ```

2. Visit the login URL:
   ```
   http://localhost:8001/oauth/login/
   ```

3. You should be redirected to your SVA OAuth provider's consent screen.

4. After approving, you'll be redirected back to your app.

## Troubleshooting

### Import Error

If you get `ModuleNotFoundError: No module named 'sva_oauth_client'`:

1. Make sure the package is installed: `pip list | grep sva-oauth-client`
2. Make sure your virtual environment is activated
3. Try reinstalling: `pip install --upgrade sva-oauth-client`

### Settings Not Found

If you get errors about missing settings:

1. Make sure all required settings are in your `settings.py`
2. Check that `sva_oauth_client` is in `INSTALLED_APPS`
3. Verify environment variables are set correctly

### OAuth Errors

If you get OAuth-related errors:

1. Verify `SVA_OAUTH_CLIENT_ID` and `SVA_OAUTH_CLIENT_SECRET` are correct
2. Check that `SVA_OAUTH_REDIRECT_URI` matches exactly what's registered in your OAuth app
3. Ensure `SVA_DATA_TOKEN_SECRET` matches the secret in your SVA OAuth provider
4. Check that your SVA OAuth provider is running and accessible

## Next Steps

- Read the [README.md](README.md) for detailed usage examples
- Check out the [API Reference](README.md#api-reference)
- See [Examples](README.md#examples) for common use cases


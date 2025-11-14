# Quick Start Guide

Get up and running with `sva-oauth-client` in 5 minutes!

## Installation

```bash
pip install sva-oauth-client
```

## Minimal Setup

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
SVA_OAUTH_BASE_URL = 'http://localhost:8000'
SVA_OAUTH_CLIENT_ID = 'your_client_id'
SVA_OAUTH_CLIENT_SECRET = 'your_client_secret'
SVA_OAUTH_REDIRECT_URI = 'http://localhost:8001/oauth/callback/'
SVA_DATA_TOKEN_SECRET = 'your_data_token_secret'
```

### 3. Add URLs

```python
# urls.py
from django.urls import include

urlpatterns = [
    path('oauth/', include('sva_oauth_client.urls')),
]
```

### 4. Create a View

```python
# views.py
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data

@sva_oauth_required
def dashboard(request):
    blocks = get_blocks_data(request.session)
    return render(request, 'dashboard.html', {'blocks': blocks})
```

### 5. Add Login Link

```django
<!-- template.html -->
<a href="{% url 'sva_oauth_client:login' %}">Sign In with SVA</a>
```

## That's It!

Your app now supports SVA OAuth authentication. Users can:
1. Click "Sign In with SVA"
2. Approve consent on SVA
3. Get redirected back with all their blocks data

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [examples/](examples/) for more use cases
- See [INSTALLATION.md](INSTALLATION.md) for production setup


# Migration Guide: v1.0.1 to v2.0.0

This guide helps you migrate from the old API to the new simplified API in v2.0.0.

## What's New

v2.0.0 introduces a **simplified API** that reduces boilerplate code and makes the package much easier to use. All existing code continues to work - this is a **backward-compatible** release.

## Key Improvements

1. **Simplified Facade API**: New `get_sva()` function provides easy access to all functionality
2. **Session Manager**: Centralized session management with `SVASessionManager`
3. **Configuration Manager**: Centralized configuration with `SVAConfig`
4. **Template-based Views**: Views now use Django templates instead of inline HTML
5. **Better Code Organization**: Clear separation of concerns

## Migration Steps

### Option 1: Use New Simplified API (Recommended)

The new API is much simpler and requires less code:

**Before (v1.0.1):**
```python
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client.utils import get_blocks_data, get_userinfo

@sva_oauth_required
def my_view(request):
    blocks_data = get_blocks_data(request.session)
    userinfo = get_userinfo(request.session)
    
    email = blocks_data.get('email') if blocks_data else None
    name = blocks_data.get('name') if blocks_data else None
    
    return render(request, 'template.html', {
        'blocks': blocks_data,
        'userinfo': userinfo,
        'email': email,
        'name': name,
    })
```

**After (v2.0.0 - Simplified):**
```python
from sva_oauth_client import get_sva
from sva_oauth_client.decorators import sva_oauth_required

@sva_oauth_required
def my_view(request):
    sva = get_sva(request)
    
    blocks = sva.get_blocks()
    userinfo = sva.get_userinfo()
    email = sva.get_block('email')
    name = sva.get_block('name')
    
    return render(request, 'template.html', {
        'blocks': blocks,
        'userinfo': userinfo,
        'email': email,
        'name': name,
    })
```

### Option 2: Keep Existing Code (No Changes Required)

All existing code continues to work without any changes. The old utility functions are still available and work exactly as before.

## New Features

### Simplified Block Access

**Before:**
```python
blocks_data = get_blocks_data(request.session)
if blocks_data:
    email = blocks_data.get('email')
    has_phone = 'phone' in blocks_data
```

**After:**
```python
sva = get_sva(request)
email = sva.get_block('email')
has_phone = sva.has_block('phone')
```

### Configuration Validation

**New:**
```python
from sva_oauth_client import SVAConfig

# Validate configuration
is_valid, missing = SVAConfig.validate()
if not is_valid:
    print(f"Missing settings: {missing}")
```

### Session Management

**New:**
```python
from sva_oauth_client import SVASessionManager

session_mgr = SVASessionManager(request.session)
session_mgr.store_tokens(token_response)
blocks = session_mgr.get_blocks_data()
```

## Breaking Changes

**None!** This release is fully backward compatible. All existing code will continue to work.

## Deprecations

None. All old APIs remain fully supported.

## Benefits of Migrating

1. **Less Code**: The new API requires significantly less boilerplate
2. **More Readable**: Code is more intuitive and easier to understand
3. **Better IDE Support**: Better autocomplete and type hints
4. **Easier Testing**: Facade pattern makes mocking easier
5. **Future-Proof**: New features will be added to the simplified API first

## Examples

See `examples/simplified_usage.py` for complete examples of the new API.

## Questions?

If you have any questions about migration, please open an issue on GitHub.







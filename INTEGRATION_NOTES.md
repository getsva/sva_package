# SVA Package Integration Notes: New Connection Management

## Overview

The SVA connection management system has been redesigned. This document explains how the `sva_oauth_client` package integrates with the new architecture.

## Package Status

### ✅ No Changes Required

The `sva_oauth_client` package **does not need changes** because:

1. **OAuth Flow Unchanged**: The OAuth 2.0 authorization code flow remains the same
2. **Token Endpoints Unchanged**: `/oauth/token/` and `/oauth/userinfo/` work the same way
3. **Userinfo Response Unchanged**: The response format is the same
4. **Data Token Unchanged**: JWT data token format is the same

## What Changed (Server-Side Only)

### New Services (SVA Server)
- `ConnectionService` - Manages connections
- `DataSharingService` - Manages sharing blobs
- `ConnectionRegistry` - Manages app metadata

### New APIs (SVA Server)
- Batch operations
- Health checks
- Statistics
- Metadata registry

### Enhanced Features (SVA Server)
- Manual scope protection
- Event-driven updates
- Webhook support
- Health monitoring

## Integration Points

### 1. OAuth Flow

The package handles OAuth flow which remains unchanged:

```python
from sva_oauth_client import get_sva

@sva_oauth_required
def my_view(request):
    sva = get_sva(request)
    email = sva.get_block('email')
    # Works exactly as before
```

### 2. Userinfo Endpoint

The package calls `/oauth/userinfo/` which:
- Still returns encrypted sharing blob
- Still returns approved scopes
- Still filters by approved scopes
- Works exactly as before

### 3. Data Token

The package decodes data_token JWT which:
- Still contains user claims
- Still filtered by approved scopes
- Works exactly as before

## Optional Enhancements

While not required, you could enhance the package with:

### 1. Connection Health Check

```python
# Optional: Add method to check connection health
def check_connection_health(session):
    """Check health of current connection"""
    # Would require API call to SVA Server
    # Not part of OAuth flow, so optional
    pass
```

### 2. Connection Statistics

```python
# Optional: Add method to get connection stats
def get_connection_stats(session):
    """Get connection statistics"""
    # Would require API call to SVA Server
    # Not part of OAuth flow, so optional
    pass
```

These are **optional** and not part of the core OAuth functionality.

## Architecture

```
sva_oauth_client Package
    ↓
OAuth Flow (authorize → token → userinfo)
    ↓
SVA OAuth Server
    ↓
SVA Server (ConnectionService)
    ↓
UserAppConnection (Database)
```

## Key Points

1. **Backward Compatible**: All existing code works
2. **No Breaking Changes**: OAuth flow unchanged
3. **Server-Side Only**: Changes are in SVA Server, not package
4. **Optional Features**: New features are optional enhancements

## Testing

### Test OAuth Flow

```python
from sva_oauth_client.decorators import sva_oauth_required
from sva_oauth_client import get_sva

@sva_oauth_required
def test_view(request):
    sva = get_sva(request)
    # Should work exactly as before
    email = sva.get_block('email')
    return {'email': email}
```

### Test Userinfo

```python
from sva_oauth_client.utils import get_userinfo

def test_userinfo(request):
    userinfo = get_userinfo(request.session)
    # Should return same format as before
    return {'userinfo': userinfo}
```

## Migration

### For Package Users

**No migration needed!** The package works exactly as before.

### For Package Developers

If you want to add new features:

1. **Add Health Check Method** (optional)
   ```python
   def check_connection_health(session):
       # Make API call to SVA Server
       # Return health status
   ```

2. **Add Statistics Method** (optional)
   ```python
   def get_connection_stats(session):
       # Make API call to SVA Server
       # Return statistics
   ```

3. **Add Batch Operations** (optional)
   ```python
   def batch_revoke_connections(session, connection_ids):
       # Make API call to SVA Server
       # Revoke connections
   ```

These are **optional enhancements** and not required for OAuth functionality.

## Troubleshooting

### Issue: Userinfo returns 401

**Cause**: Connection may be revoked or inactive

**Solution**: 
- Check connection in SVA Client app
- Verify connection is active
- Check approved scopes

### Issue: Claims are empty

**Cause**: Approved scopes may not match requested scopes

**Solution**:
- Check approved scopes in connection
- Verify scopes match requested scopes
- Check sharing blob exists

### Issue: Token expired

**Cause**: Access token expired

**Solution**:
- Package should handle refresh automatically
- If not, user needs to re-authenticate

## Conclusion

The `sva_oauth_client` package requires **no changes**. The new architecture is backward compatible and enhances server-side functionality without affecting the OAuth client package.

## Future Considerations

If you want to add connection management features to the package:

1. **Add Connection Management Module**
   - Methods for managing connections
   - Health checks
   - Statistics

2. **Add Webhook Support**
   - Receive connection events
   - Update local state

3. **Add Admin Features**
   - View connections
   - Manage scopes
   - Monitor health

These are **future enhancements** and not required for current functionality.


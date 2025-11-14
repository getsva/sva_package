# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added
- Initial release
- Complete OAuth 2.0 Authorization Code Flow with PKCE support
- `SVAOAuthClient` class for OAuth operations
- Django views for login, callback, and logout
- Decorators: `@sva_oauth_required` and `@sva_blocks_required`
- Utility functions for session management
- Support for all SVA identity blocks
- Comprehensive error handling
- Full type hints support
- Complete documentation and examples

### Features
- Authorization URL generation with PKCE
- Token exchange and refresh
- Data token decoding and validation
- Userinfo retrieval
- Blocks data extraction
- Session-based token storage
- CSRF protection via state parameter


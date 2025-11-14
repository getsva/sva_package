# Building and Distributing the Package

## Building the Package

### Prerequisites

```bash
pip install build twine
```

### Build Distribution Packages

```bash
# Build both wheel and source distribution
python -m build

# This creates:
# - dist/sva_oauth_client-1.0.0-py3-none-any.whl
# - dist/sva_oauth_client-1.0.0.tar.gz
```

### Build Options

```bash
# Build only wheel
python -m build --wheel

# Build only source distribution
python -m build --sdist
```

## Testing the Build

### Install from Local Build

```bash
# Install from wheel
pip install dist/sva_oauth_client-1.0.0-py3-none-any.whl

# Or install from source distribution
pip install dist/sva_oauth_client-1.0.0.tar.gz

# Or install in development mode
pip install -e .
```

### Verify Installation

```bash
python -c "import sva_oauth_client; print(sva_oauth_client.__version__)"
```

## Publishing to PyPI

### Test PyPI (Recommended First)

```bash
# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Install from Test PyPI
pip install --index-url https://test.pypi.org/simple/ sva-oauth-client
```

### Production PyPI

```bash
# Upload to PyPI
twine upload dist/*

# Install from PyPI
pip install sva-oauth-client
```

### Authentication

You'll need to create API tokens:
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Use it with twine:

```bash
twine upload --username __token__ --password <your_token> dist/*
```

## Version Management

### Update Version

1. Update version in:
   - `setup.py` (version parameter)
   - `pyproject.toml` (version field)
   - `sva_oauth_client/__init__.py` (__version__)

2. Update `CHANGELOG.md`

3. Build and test:

```bash
python -m build
pip install dist/sva_oauth_client-<new_version>-py3-none-any.whl
```

## Development Installation

For development, install in editable mode:

```bash
pip install -e ".[dev]"
```

This installs the package in development mode with dev dependencies.

## Package Structure

```
sva-oauth-client/
├── sva_oauth_client/      # Main package
│   ├── __init__.py
│   ├── client.py          # OAuth client
│   ├── decorators.py      # Decorators
│   ├── utils.py           # Utilities
│   ├── views.py           # Django views
│   └── urls.py            # URL patterns
├── examples/              # Usage examples
├── setup.py               # Setup configuration
├── pyproject.toml         # Modern Python packaging
├── MANIFEST.in            # Package data
├── README.md              # Documentation
├── LICENSE                # License file
└── requirements.txt       # Dependencies (optional)
```

## Checklist Before Publishing

- [ ] Version updated in all files
- [ ] CHANGELOG.md updated
- [ ] README.md is complete and accurate
- [ ] All tests pass
- [ ] Package builds successfully
- [ ] Package installs correctly
- [ ] All imports work
- [ ] Documentation is up to date
- [ ] License file included
- [ ] .gitignore is configured

## Troubleshooting

### Build Errors

If you get build errors:

1. Check that all required files are present
2. Verify `MANIFEST.in` includes all necessary files
3. Check `setup.py` or `pyproject.toml` for errors
4. Ensure all dependencies are listed

### Import Errors After Installation

If imports fail after installation:

1. Verify package is installed: `pip list | grep sva-oauth-client`
2. Check Python path: `python -c "import sys; print(sys.path)"`
3. Reinstall: `pip uninstall sva-oauth-client && pip install dist/...`

### Upload Errors

If upload to PyPI fails:

1. Check credentials/token
2. Verify package name is available
3. Ensure version number is unique
4. Check network connection


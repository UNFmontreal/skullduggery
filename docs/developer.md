# Developer Guide

## Setting Up Development Environment

### Prerequisites
- Python 3.8 or higher
- Git
- pip or conda

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/UNFmontreal/skullduggery.git
   cd skullduggery
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode with test dependencies**
   ```bash
   pip install -e ".[test,datalad]"
   ```

## Project Structure

```
skullduggery/
├── src/skullduggery/          # Main package
│   ├── __init__.py            # Package metadata
│   ├── align.py               # ANTs registration
│   ├── bids.py                # BIDS filtering utilities
│   ├── mask.py                # Defacing mask generation
│   ├── report.py              # Report generation
│   ├── run.py                 # CLI entry point
│   ├── template.py            # Template retrieval
│   ├── utils.py               # Utility functions
│   ├── workflow.py            # Main defacing workflow
│   └── data/                  # Data files
├── tests/                     # Unit tests
├── docs/                      # Documentation
├── pyproject.toml             # Project configuration
└── README.md                  # User guide
```

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_bids.py -v
```

### Run with coverage report
```bash
pytest tests/ --cov=skullduggery --cov-report=html
```

### Run specific test
```bash
pytest tests/test_bids.py::test_filter_pybids_any -v
```

## Code Quality

### Linting

We use flake8, black, and pylint for code quality:

```bash
# Format code with black
black src/skullduggery tests

# Check linting
flake8 src/skullduggery tests
pylint src/skullduggery tests
```

### Pre-commit Hooks

Set up pre-commit hooks to automatically check code quality:

```bash
pre-commit install
```

See [pre-commit-config.md](pre-commit-config.md) for configuration details.

## Documentation

### Building Documentation

```bash
cd docs
make html
```

Documentation will be generated in `docs/_build/html/`.

### Writing Docstrings

Use Google-style docstrings for all public functions:

```python
def my_function(param1: str, param2: int) -> bool:
    """Brief description of what the function does.

    More detailed explanation of the function's behavior,
    including any important notes or caveats.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this is raised.
    """
    pass
```

## Adding New Features

### Process

1. Create a feature branch from `main`
2. Implement changes with tests
3. Run full test suite and linting
4. Update documentation
5. Create pull request with clear description

### Testing New Features

Always include unit tests for new code:

```python
def test_my_new_feature():
    """Test description of the feature."""
    result = my_new_function(test_input)
    assert result == expected_output
```

## Debugging

### Enable Debug Logging
```bash
DEBUG=1 skullduggery /path/to/dataset --debug debug
```

### Python Debugger
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

## Dependencies

### Minimal Core Dependencies
- templateflow
- coloredlogs
- pybids
- nibabel
- numpy
- antspyx
- nitransforms
- nireports

### Optional Dependencies
- datalad (for DataLad integration)

### Development Dependencies
Specified in `pyproject.toml` under `[project.optional-dependencies]`

## Version Management

Version is automatically managed from git tags via flit. To create a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

## Common Issues

### ImportError: No module named 'datalad'
Install with DataLad support:
```bash
pip install skullduggery[datalad]
```

### ANTs registration fails
Ensure antspyx is installed:
```bash
pip install antspyx
```

### Test failures
Ensure all test dependencies are installed:
```bash
pip install -e ".[test]"
pytest tests/ -v
```

## Contributing Guidelines

1. Keep commits atomic and well-documented
2. Follow PEP 8 style guidelines
3. Include tests for new functionality
4. Update docstrings and documentation
5. Ensure all tests pass before submitting PR

## Contact

For questions or issues, open an issue on [GitHub](https://github.com/UNFmontreal/skullduggery/issues).

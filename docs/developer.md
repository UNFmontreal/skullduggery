# Developer Guide

## Quick Start

```bash
# Clone and setup
git clone https://github.com/UNFmontreal/skullduggery.git
cd skullduggery
python -m venv venv
source venv/bin/activate
pip install -e ".[test,datalad]"
```

## Project Structure

```
skullduggery/
├── src/skullduggery/
│   ├── run.py              # CLI entry point
│   ├── workflow.py         # Main defacing pipeline
│   ├── align.py            # ANTs registration
│   ├── mask.py             # Mask generation
│   ├── bids.py             # BIDS utilities
│   ├── template.py         # Template handling
│   ├── report.py           # Report generation
│   └── utils.py            # Helpers
├── tests/                  # Unit tests
├── docs/                   # Documentation
└── pyproject.toml          # Project config
```

## Development Tasks

### Tests
```bash
pytest tests/                           # All tests
pytest tests/test_bids.py -v            # Single file
pytest tests/ --cov=skullduggery        # With coverage
```

### Code Quality
```bash
black src/skullduggery tests            # Format
flake8 src/skullduggery tests           # Lint
pre-commit install                      # Auto-checks
```

### Documentation
```bash
cd docs
make html                               # Build docs
```

## Docstring Format

Use Google-style docstrings:

```python
def process_image(path: str, template: str) -> bool:
    """Brief one-liner description.

    More detailed explanation if needed.

    Args:
        path: Input file path.
        template: Template name.

    Returns:
        True if successful.

    Raises:
        ValueError: If inputs are invalid.
    """
```

## Adding Features

1. Create feature branch from `main`
2. Write tests first
3. Implement feature
4. Run: `pytest tests/ && flake8 src/`
5. Update docs if needed
6. Submit PR

## Dependencies

**Core:** templateflow, pybids, nibabel, antspyx, nitransforms, nireports, coloredlogs

**Optional:** datalad (DataLad support)

**Dev:** specified in pyproject.toml

## Debugging

```bash
DEBUG=1 skullduggery /path/to/dataset --debug debug
```

Or add breakpoint in code:
```python
import pdb; pdb.set_trace()
```

## Common Issues

| Issue | Solution |
|-------|----------|
| `ImportError: datalad` | `pip install skullduggery[datalad]` |
| ANTs registration fails | `pip install antspyx` |
| Tests fail | `pip install -e ".[test]" && pytest tests/` |

## Contributing

- Keep commits atomic and meaningful
- Follow PEP 8
- Include tests for new code
- Update docstrings
- Ensure all tests pass (`pytest tests/`)

**Questions?** Open an issue on [GitHub](https://github.com/UNFmontreal/skullduggery/issues)

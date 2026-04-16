# Visual Studio Code Setup for Skullduggery Development

## Extensions

Install these recommended extensions in VS Code:

### Python Development
- **Python** (ms-python.python) - Official Python extension
- **Pylance** (ms-python.vscode-pylance) - Python language server
- **autoDocstring** (njpwerner.autodocstring) - Auto-generate docstrings

### Code Quality
- **black** (ms-python.black-formatter) - Code formatter
- **Pylint** (ms-python.pylint) - Linter integration
- **flake8** (charliermarsh.ruff) - Linter (alternative)

### Git & Version Control
- **Git Graph** (mhutchie.git-graph) - Visual git history
- **Pre-commit** (jjroelfs.pre-commit) - Pre-commit hook UI

### Documentation
- **reStructuredText** (lextudio.restructuredtext) - RST support
- **Markdown Preview Enhanced** (shd101wyy.markdown-preview-enhanced) - Better Markdown preview

## Configuration

### .vscode/settings.json

Create `.vscode/settings.json` in the project root:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.pylintPath": "${workspaceFolder}/venv/bin/pylint",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "editor.rulers": [120],
  "editor.wordWrapColumn": 120,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true,
    "**/.coverage": true
  },
  "search.exclude": {
    "**/.venv": true,
    "**/venv": true,
    "**/__pycache__": true,
    "**/node_modules": true
  }
}
```

### .vscode/launch.json

Create `.vscode/launch.json` for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Debug CLI",
      "type": "python",
      "request": "launch",
      "module": "skullduggery.run",
      "args": ["/path/to/bids/dataset"],
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Python: Debug Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v",
        "--tb=short"
      ],
      "console": "integratedTerminal"
    }
  ]
}
```

### .vscode/extensions.json

Create `.vscode/extensions.json` for recommended extensions:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "ms-python.pylint",
    "njpwerner.autodocstring",
    "mhutchie.git-graph",
    "jjroelfs.pre-commit",
    "lextudio.restructuredtext",
    "shd101wyy.markdown-preview-enhanced"
  ]
}
```

## Workflow Tips

### Running Tests
- Use the Test Explorer (left sidebar) to run individual tests
- Press `Ctrl+Shift+D` to debug selected test
- View coverage with `pytest --cov`

### Code Formatting
- Press `Shift+Alt+F` to format current file
- Enable "Format on Save" in settings

### Git Integration
- View git history with Git Graph extension
- Use Source Control panel (Ctrl+Shift+G) for commits and branches

### Debugging
- Set breakpoints by clicking line numbers
- Use Debug Console for variable inspection
- Press F10 to step over, F11 to step into

### IntelliSense
- Press `Ctrl+Space` for autocomplete
- Press `Ctrl+Shift+Space` for parameter hints
- Hover over symbols for docstring preview

## Virtual Environment

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Select Interpreter
1. Open Command Palette (`Ctrl+Shift+P`)
2. Search for "Python: Select Interpreter"
3. Choose the venv interpreter: `./venv/bin/python`

## Pytest Integration

### Run Tests from UI
1. Click the Test Explorer icon (left sidebar)
2. Discover tests by clicking the discover button
3. Run tests individually or in groups
4. View output in the Test Results panel

### Keyboard Shortcuts
- `Ctrl+Shift+P` + "Test: Run All Tests"
- `Ctrl+Shift+P` + "Test: Rerun Last Run"

## Useful Commands

Open Command Palette with `Ctrl+Shift+P`:

- `Python: Create Terminal` - Create Python terminal with venv
- `Python: Restart Language Server` - Restart Pylance
- `Format Document` - Format current file
- `Sort Imports` - Organize imports
- `Go to Definition` - Jump to symbol definition
- `Find All References` - Find all usages of symbol

## Performance Tips

- Disable unused extensions in Settings
- Use `.python-version` for environment consistency
- Enable Pylance only for open files
- Configure `.gitignore` to exclude large folders

## Troubleshooting

### Pylance not working
1. Restart VS Code
2. Run `Python: Restart Language Server`
3. Check Python path in settings

### Tests not discovered
1. Ensure pytest is installed: `pip install pytest`
2. Close and reopen Test Explorer
3. Check file names start with `test_`

### Formatting conflicts
1. Check black and pylint are compatible versions
2. Run `black` before `pylint` (black first in pipeline)
3. Review pyproject.toml for conflicting settings

## Learn More

- [VS Code Python Documentation](https://code.visualstudio.com/docs/languages/python)
- [Pylance Documentation](https://github.com/microsoft/pylance-release)
- [Black Documentation](https://black.readthedocs.io/)

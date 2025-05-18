# Development Guide

This guide covers the project structure and development setup for Feature Implementer.

## Project Structure

```
feature-implementer/              # Project Root
├── README.md                    # Project overview
├── LICENSE                      # MIT License
├── pyproject.toml              # Build/package configuration
├── .gitignore
└── src/
    └── feature_implementer_core/ # Main package
        ├── __init__.py
        ├── app.py              # Flask application
        ├── cli.py              # CLI implementation
        ├── config.py           # Configuration
        ├── database.py         # SQLite handling
        ├── file_utils.py       # File operations
        ├── prompt_generator.py # Core logic
        ├── feature_implementation_template.md  # Default template
        ├── templates/          # Flask templates
        │   ├── index.html
        │   ├── template_manager.html
        │   └── macros.html
        ├── static/             # Web assets
        │   ├── css/
        │   ├── js/
        │   └── ...
        └── prompts/           # Template storage
            └── example_custom_prompt.md
```

## Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/paulwenner/feature-implementer.git
   cd feature-implementer
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=feature_implementer_core

# Run specific test file
pytest tests/test_prompt_generator.py
```

### Code Style

We use Black for code formatting and flake8 for linting:

```bash
# Format code
black src/ tests/

# Check style
flake8 src/ tests/
```

### Type Checking

```bash
# Run mypy
mypy src/
```

## Building and Publishing

1. **Update Version**
   - Edit version in `pyproject.toml`
   - Update CHANGELOG.md

2. **Build Package**
   ```bash
   python -m build
   ```

3. **Test Distribution**
   ```bash
   pip install dist/feature_implementer-*.whl
   ```

4. **Upload to PyPI**
   ```bash
   python -m twine upload dist/*
   ```

## Architecture Overview

### Core Components

1. **Web Interface (`app.py`)**
   - Flask application
   - File browser
   - Template management UI
   - Prompt generation interface

2. **CLI Interface (`cli.py`)**
   - Command parsing
   - File operations
   - Template management
   - Prompt generation

3. **Prompt Generator (`prompt_generator.py`)**
   - Core logic for combining:
     - Code context
     - Jira descriptions
     - Templates
     - Additional instructions

4. **Database (`database.py`)**
   - SQLite management
   - Template storage
   - Configuration persistence

5. **File Utils (`file_utils.py`)**
   - File operations
   - Path management
   - Content reading/writing

### Data Flow

1. **Input Processing**
   - File selection/reading
   - Template selection
   - Instruction gathering

2. **Prompt Generation**
   - Context extraction
   - Template application
   - Markdown formatting

3. **Output Handling**
   - File export
   - Web display
   - CLI output

## Contributing

1. **Fork the Repository**
   - Create your feature branch
   - Make your changes
   - Add tests for new features

2. **Submit Pull Request**
   - Ensure tests pass
   - Update documentation
   - Follow code style guidelines

3. **Review Process**
   - Code review
   - CI/CD checks
   - Documentation review 
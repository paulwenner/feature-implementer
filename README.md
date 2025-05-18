# Feature Implementer

**Generate high-quality feature prompts for LLMs from your codebase.**  
A pip-installable tool that helps create well-structured prompts for LLMs by gathering context from relevant code files within your project.

## ⚡ Quickstart

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install the package
pip install feature-implementer

# Run in your project directory
cd /your/project
feature-implementer
```

Open your browser at http://127.0.0.1:4605 and start generating prompts!

## ✨ Features

- 🌐 **Interactive Web UI** and powerful CLI
- 📁 Smart context gathering from your codebase
- 🎯 Custom prompt templates with local storage
- 🔄 Jira integration for ticket descriptions
- 📝 Export prompts as Markdown files
- 🌙 Light/dark mode support

## 📦 Installation

Install from PyPI:

```bash
pip install feature-implementer
```

Or get the latest development version:

```bash
git clone https://github.com/paulwenner/feature-implementer.git
cd feature-implementer
pip install -e .
```

## 🚀 Basic Usage

### Web UI

1. Start the server: `feature-implementer`
2. Open http://127.0.0.1:4605 in your browser
3. Select relevant code files from your project
4. Add Jira ticket description and instructions
5. Generate and export your prompt!

### CLI

Generate a prompt with context files:

```bash
feature-implementer-cli --context-files src/app.py src/models.py \
                       --jira "FEAT-123: New feature" \
                       --output prompt.md
```

## 📚 Documentation

For detailed information, check out:

- [Complete Usage Guide](docs/usage.md)
- [Template Management](docs/templates.md)
- [CLI Reference](docs/cli.md)
- [Development Guide](docs/development.md)

## 🛠️ Configuration Options

Quick reference for common settings:

```bash
# Custom port
feature-implementer --port 5001

# Custom directories
feature-implementer --working-dir /path/to/project --prompts-dir /path/to/prompts

# Production mode
feature-implementer --prod --workers 4
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 

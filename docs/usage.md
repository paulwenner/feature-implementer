# Complete Usage Guide

This guide covers all aspects of using Feature Implementer, including both the Web UI and CLI interfaces.

## Web UI Usage

### Starting the Server

The web interface is the recommended way to use Feature Implementer. To start it:

```bash
feature-implementer
```

This typically runs on `http://127.0.0.1:4605`. You can customize the server settings:

```bash
# Run on a different port
feature-implementer --port 5001

# Run accessible on your network (use with caution)
feature-implementer --host 0.0.0.0 

# Run in production mode using gunicorn (if installed)
feature-implementer --prod --workers 4

# Disable debug mode
feature-implementer --no-debug
```

### Using the Web Interface

1. Navigate to the web interface in your browser
2. The file explorer shows files relative to your current directory
3. Select files from your codebase to provide context
4. Enter the Jira ticket description (or path to file)
5. Add implementation instructions (or path to file)
6. Select a prompt template
7. Click "Generate Prompt"
8. Copy or export the generated prompt as Markdown

### Directory Configuration

You can specify custom directories for your project and prompts:

```bash
# Use a different working directory
feature-implementer --working-dir /path/to/project

# Specify prompt templates directory
feature-implementer --prompts-dir /path/to/prompts

# Combine multiple settings
feature-implementer --working-dir /app/project --prompts-dir /app/prompts
```

## CLI Usage

The CLI interface is perfect for automation and scripting. Two main commands are available:

- `feature-implementer`: Runs the web server
- `feature-implementer-cli`: Core functions for prompt generation

### Generating Prompts via CLI

Basic prompt generation:

```bash
feature-implementer-cli --context-files src/app.py src/models.py \
                       --jira "FEAT-123: New feature" \
                       --output prompt.md
```

Additional options:

```bash
# Use a specific template
feature-implementer-cli --template-id 2 --context-files ... --jira ...

# Read Jira description from file
feature-implementer-cli --context-files ... --jira path/to/description.txt

# Custom working directory
feature-implementer-cli --working-dir /path/to/project \
                       --context-files app.py models.py \
                       --jira "FEAT-456: Add new feature"

# Custom prompts directory
feature-implementer-cli --prompts-dir /path/to/prompts \
                       --context-files app.py \
                       --jira "FEAT-789: New feature"
```

## Best Practices

1. **Context Selection**
   - Choose files that are directly relevant to the feature
   - Include interface definitions and related components
   - Don't include entire large files if only a section is relevant

2. **Jira Descriptions**
   - Be specific about requirements
   - Include acceptance criteria
   - Reference related tickets or documentation

3. **Additional Instructions**
   - Specify architectural constraints
   - Mention coding standards to follow
   - List any dependencies or version requirements

4. **Template Selection**
   - Use specialized templates for different types of features
   - Create custom templates for recurring patterns
   - Keep templates focused and maintainable 
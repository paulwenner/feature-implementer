# CLI Reference

Feature Implementer provides two main command-line interfaces:
- `feature-implementer`: Web server management
- `feature-implementer-cli`: Core functionality

## Web Server Command (`feature-implementer`)

### Basic Usage

```bash
feature-implementer [options]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port PORT` | Server port | 4605 |
| `--host HOST` | Server host | 127.0.0.1 |
| `--working-dir DIR` | Project directory | Current directory |
| `--prompts-dir DIR` | Templates directory | System default |
| `--prod` | Production mode | False |
| `--workers N` | Number of workers (prod mode) | 1 |
| `--no-debug` | Disable debug mode | False |

### Examples

```bash
# Basic start
feature-implementer

# Custom port and host
feature-implementer --port 5001 --host 0.0.0.0

# Production deployment
feature-implementer --prod --workers 4 --host 0.0.0.0

# Custom directories
feature-implementer --working-dir /path/to/project --prompts-dir /path/to/prompts
```

## Core CLI (`feature-implementer-cli`)

### Prompt Generation

```bash
feature-implementer-cli --context-files FILE [FILE ...] \
                       --jira DESCRIPTION \
                       [options]
```

#### Required Arguments

| Argument | Description |
|----------|-------------|
| `--context-files` | Space-separated list of source files |
| `--jira` | Jira ticket description or file path |

#### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--output FILE` | Output file path | stdout |
| `--template-id ID` | Template ID to use | Default template |
| `--instructions TEXT` | Additional instructions | None |
| `--working-dir DIR` | Project directory | Current directory |
| `--prompts-dir DIR` | Templates directory | System default |

### Template Management

```bash
# List templates
feature-implementer-cli --list-templates

# Create template
feature-implementer-cli --create-template NAME \
                       --template-content FILE \
                       --template-description DESC

# Set default
feature-implementer-cli --set-default ID

# Delete template
feature-implementer-cli --delete-template ID

# Reset templates
feature-implementer-cli --reset-templates
```

### Examples

```bash
# Generate prompt with multiple files
feature-implementer-cli --context-files src/app.py src/models.py \
                       --jira "FEAT-123: New API endpoint" \
                       --instructions "Use FastAPI" \
                       --output prompt.md

# Use specific template
feature-implementer-cli --template-id 2 \
                       --context-files api.py \
                       --jira ticket.txt

# Create new template
feature-implementer-cli --create-template "API Template" \
                       --template-content template.md \
                       --template-description "Template for API endpoints"

# List all templates
feature-implementer-cli --list-templates

# Set default template
feature-implementer-cli --set-default 3
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FEATURE_IMPLEMENTER_PORT` | Server port | 4605 |
| `FEATURE_IMPLEMENTER_HOST` | Server host | 127.0.0.1 |
| `FEATURE_IMPLEMENTER_WORKING_DIR` | Project directory | Current directory |
| `FEATURE_IMPLEMENTER_PROMPTS_DIR` | Templates directory | System default |
| `FEATURE_IMPLEMENTER_DEBUG` | Debug mode | False |

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | File not found |
| 4 | Template error |
| 5 | Database error | 
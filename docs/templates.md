# Template Management

Feature Implementer provides a flexible template system for customizing how prompts are generated. This guide covers all aspects of template management.

## Template Storage

Templates are stored in a local SQLite database (`.feature_implementer.db`) located in your system's application data directory:

- Linux: `~/.local/share/feature_implementer/`
- macOS: `~/Library/Application Support/feature_implementer/`
- Windows: `%APPDATA%\feature_implementer\` (e.g., `C:\Users\YourUser\AppData\Roaming\feature_implementer\`)

If these locations are inaccessible, the app creates a `.feature_implementer_data` directory in your workspace.

## Web UI Template Management

### Accessing the Template Manager

1. Start the web server: `feature-implementer`
2. Navigate to the "Template Manager" page (link in header/footer)

### Managing Templates

1. **View Templates**
   - Browse existing templates
   - See template descriptions and usage

2. **Create Templates**
   - Click "New Template"
   - Fill in the template form
   - Use essential placeholders:
     - `{relevant_code_context}`: Selected code files content
     - `{jira_description}`: Jira ticket content
     - `{additional_instructions}`: Extra implementation notes

3. **Edit Templates**
   - Modify existing templates
   - Update descriptions
   - Change placeholder usage

4. **Set Default Template**
   - Click "Set Default" on any template
   - Used when no specific template is selected

5. **Delete Templates**
   - Remove unused templates
   - Cannot delete the system default template

6. **Reset to Defaults**
   - Click "Reset Templates"
   - Restores initial template set
   - ⚠️ Deletes all custom templates

## CLI Template Management

Manage templates directly from the command line:

```bash
# List all templates
feature-implementer-cli --list-templates

# Create template from file
feature-implementer-cli --create-template "My API Template" \
                       --template-content path/to/template.txt \
                       --template-description "Template for API endpoints"

# Set default template
feature-implementer-cli --set-default 3

# Delete template
feature-implementer-cli --delete-template 4

# Reset to defaults
feature-implementer-cli --reset-templates
```

## Template Writing Guide

### Basic Structure

A good template should include:

1. **Context Section**
   - Project background
   - Feature requirements
   - Technical constraints

2. **Implementation Guidelines**
   - Coding standards
   - Architecture patterns
   - Testing requirements

3. **Placeholders**
   - Strategic placement of context
   - Clear instructions
   - Additional requirements

### Example Template

```markdown
# Feature Implementation: {feature_name}

## Context
{jira_description}

## Relevant Code
{relevant_code_context}

## Implementation Requirements
{additional_instructions}

## Expected Deliverables
- Implementation code
- Unit tests
- Documentation updates
- Migration scripts (if needed)
```

### Best Practices

1. **Keep It Focused**
   - One template per type of feature
   - Clear purpose and scope
   - Avoid redundant information

2. **Use Clear Placeholders**
   - Descriptive names
   - Consistent formatting
   - Document expected content

3. **Include Validation**
   - Required fields
   - Format checking
   - Error messages

4. **Maintain Templates**
   - Regular reviews
   - Update for new requirements
   - Remove obsolete templates 
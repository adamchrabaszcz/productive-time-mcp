# productive-time-mcp

MCP (Model Context Protocol) server for Productive.io time tracking operations.

This is a companion MCP to [berwickgeek/productive-mcp](https://github.com/berwickgeek/productive-mcp) that adds time tracking capabilities not included in the original.

## Features

- **Time Entry Management**: Create, read, update, and delete time entries
- **Time Reports**: Get hours summaries (worked, client, internal, holidays)
- **Employee Hours**: Search employees by name and get their workload
- **Smart Period Calculation**: Automatic month detection based on current date

## Installation

### Using uvx (recommended)

```bash
uvx --from git+https://github.com/adamchrabaszcz/productive-time-mcp productive-time-mcp
```

### Using pip

```bash
pip install git+https://github.com/adamchrabaszcz/productive-time-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PRODUCTIVE_API_TOKEN` | Yes | Your Productive.io API token |
| `PRODUCTIVE_ORG_ID` | Yes | Your organization ID |
| `PRODUCTIVE_USER_ID` | No | Your person ID (enables "me" references) |

### Getting Your IDs

**Organization ID:**
- Go to Productive.io Settings
- The org ID is visible in API requests or can be found via the API

**Person ID:**
```bash
curl -H "X-Auth-Token: YOUR_TOKEN" \
     -H "X-Organization-Id: YOUR_ORG_ID" \
     "https://api.productive.io/api/v2/people?filter[email]=your.email@company.com"
```

**API Token:**
1. Go to Productive > Settings > API Integrations
2. Create a new token or use existing

## Usage with Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "productive-time": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/adamchrabaszcz/productive-time-mcp", "productive-time-mcp"],
      "env": {
        "PRODUCTIVE_API_TOKEN": "${PRODUCTIVE_API_TOKEN}",
        "PRODUCTIVE_ORG_ID": "${PRODUCTIVE_ORG_ID}",
        "PRODUCTIVE_USER_ID": "${PRODUCTIVE_USER_ID}"
      }
    }
  }
}
```

## Available Tools

### Read Operations

| Tool | Description |
|------|-------------|
| `get_person` | Find a person by name or email |
| `get_time_reports` | Get hours summary for a period |
| `get_time_entries` | List time entries for a period |
| `get_time_entry` | Get single time entry with details |
| `get_my_hours` | Get current user's hours summary |
| `get_employee_hours` | Get any employee's hours by name |

### Write Operations

| Tool | Description |
|------|-------------|
| `create_time_entry` | Log time to a service/task |
| `update_time_entry` | Modify existing time entry |
| `delete_time_entry` | Remove a time entry |

## Examples

### Get My Hours This Month

```
"Show my hours for this month"
```

### Check Employee Hours

```
"How many hours did John Doe work this month?"
"Get Maria's worklog for January 2024"
```

### Log Time

```
"Log 2 hours on API integration today"
```

## Development

```bash
# Clone and install
git clone https://github.com/adamchrabaszcz/productive-time-mcp
cd productive-time-mcp
pip install -e ".[dev]"

# Run tests
pytest

# Run locally
export PRODUCTIVE_API_TOKEN="your-token"
export PRODUCTIVE_ORG_ID="your-org-id"
python -m productive_time_mcp
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Related Projects

- [berwickgeek/productive-mcp](https://github.com/berwickgeek/productive-mcp) - Tasks, projects, boards (complementary MCP)
- [druellan/productive-mcp](https://github.com/druellan/productive-mcp) - Alternative Python implementation

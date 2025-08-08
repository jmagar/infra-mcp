import logging

from typing import Any

logger = logging.getLogger(__name__)

def _tail_file(filepath: str, lines: int) -> list[str]:
    """Reads the last N lines from a file."""
    try:
        with open(filepath) as f:
            # Read all lines and return the last N
            return f.readlines()[-lines:]
    except FileNotFoundError:
        logger.warning(f"Log file not found: {filepath}")
        return [f"ERROR: Log file not found at {filepath}"]
    except Exception as e:
        logger.error(f"Error reading log file {filepath}: {e}")
        return [f"ERROR: Could not read {filepath}: {e}"]

async def get_dev_logs(lines: int = 50) -> dict[str, Any]:
    """
    Tails the development log files for the API and MCP servers.

    This tool reads the last N lines from both `logs/api_server.log` and
    `logs/mcp_server.log` to provide a snapshot of recent activity.

    Args:
        lines: The number of lines to retrieve from each log file.

    Returns:
        A dictionary containing the logs from both servers.
    """
    logger.info(f"Fetching last {lines} lines from development logs.")

    api_log_path = "logs/api_server.log"
    mcp_log_path = "logs/mcp_server.log"

    api_logs = _tail_file(api_log_path, lines)
    mcp_logs = _tail_file(mcp_log_path, lines)

    return {
        "api_server_logs": {
            "log_file": api_log_path,
            "line_count": len(api_logs),
            "lines": [line.strip() for line in api_logs],
        },
        "mcp_server_logs": {
            "log_file": mcp_log_path,
            "line_count": len(mcp_logs),
            "lines": [line.strip() for line in mcp_logs],
        },
        "summary": f"Retrieved last {lines} lines from API and MCP server logs.",
    }

# Tool registration metadata for MCP server
DEVELOPMENT_TOOLS: dict[str, dict[str, Any]] = {
    "get_dev_logs": {
        "name": "get_dev_logs",
        "description": "Tails the development log files (api_server.log and mcp_server.log).",
        "parameters": {
            "type": "object",
            "properties": {
                "lines": {
                    "type": "integer",
                    "description": "The number of lines to retrieve from each log file.",
                    "default": 50,
                },
            },
            "required": [],
        },
        "function": get_dev_logs,
    }
}

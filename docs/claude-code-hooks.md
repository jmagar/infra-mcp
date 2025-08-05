# Claude Code Hooks Configuration Guide

This document explains the Claude Code hooks implemented for the Infrastructor project to automatically prevent common code quality issues identified in PR reviews.

## Overview

Our hooks configuration prevents common code quality issues and enforces best practices, including:
- **SQLAlchemy Issues**: Mutable default values in Column definitions
- **Type Safety**: Deprecated typing module imports (Optional, List, Dict, Union)
- **Architecture Violations**: Direct SSH client creation bypassing service layer
- **Time Handling**: Timezone-naive datetime objects
- **Database Safety**: Non-idempotent SQL operations
- **Resource Management**: Multiple database connection pools
- **Configuration**: Hardcoded timeout and retry values
- **Observability**: Missing correlation IDs in logging
- **Error Handling**: Missing exception chaining
- **Code Quality**: Automatic formatting with ruff

## Hook Configuration Location

The hooks are configured in `.claude/settings.json` and are automatically loaded when Claude Code starts.

### Hook Directory Structure
```
.claude/
├── settings.json              # Main hook configuration
└── hooks/
    ├── pre_tool_use_write.py  # PreToolUse hook for Write operations
    └── pre_tool_use_edit.py   # PreToolUse hook for Edit operations
```

**Implementation Note**: The hooks use external Python scripts rather than inline commands for better maintainability, debugging, and error handling. Each script processes the tool input via stdin and outputs JSON results to stdout.

## Active Hooks

### 1. PreToolUse: SQLAlchemy Mutable Defaults Prevention

**Purpose**: Prevents the creation of SQLAlchemy Column definitions with mutable default values.

**Trigger**: Activated on `Write` tool operations

**Detection Pattern**: Regex pattern that matches Column definitions with dict or list defaults

**Blocked Code**: Column definitions using `default={}` or `default=[]` patterns

**Correct Patterns**:
```python
# ✅ ALLOWED - Use server_default for mutable types
metadata = Column(JSONB, server_default='{}')
tags = Column(JSONB, server_default='[]')
settings = Column(JSONB, server_default='{"active": true}')

# ✅ ALLOWED - Immutable defaults are fine
name = Column(String(255), default="unnamed")
active = Column(Boolean, default=True)
count = Column(Integer, default=0)
```

**Why This Matters**: Mutable defaults in SQLAlchemy create shared objects across all instances, leading to data corruption and unexpected behavior.

### 2. PreToolUse: Deprecated Type Annotations Prevention

**Purpose**: Prevents use of outdated `typing` module imports in favor of Python 3.11+ built-in types.

**Trigger**: Activated on `Write` and `Edit` tool operations

**Detection Pattern**: Regex pattern that matches imports from `typing` module for basic types

**Blocked Code**: Imports using `Optional`, `List`, `Dict`, `Union` from typing module

**Correct Patterns**:
```python
# ❌ BLOCKED - Outdated typing module imports
from typing import Optional, List, Dict, Union

# ✅ ALLOWED - Modern Python 3.11+ built-in types
def process_data(items: list[str], config: dict[str, int]) -> str | None:
    return items[0] if items else None

# ✅ ALLOWED - Complex types still need typing module
from typing import Callable, TypeVar, Generic
```

**Why This Matters**: Python 3.11+ provides built-in generics, making code cleaner and more performant without the `typing` module overhead.

### 3. PreToolUse: Direct SSH Client Creation Prevention

**Purpose**: Prevents direct SSH client instantiation in favor of centralized service architecture.

**Trigger**: Activated on `Write` and `Edit` tool operations  

**Detection Pattern**: Regex pattern that matches direct SSH client creation calls

**Blocked Code**: Direct calls to `get_ssh_client()` or `SSHClient()` constructors

**Correct Patterns**:
```python
# ❌ BLOCKED - Direct SSH client creation
ssh_client = get_ssh_client()
client = SSHClient()

# ✅ ALLOWED - Use centralized service
from src.services.unified_data_collection_service import UnifiedDataCollectionService

async def collect_system_info(device_id: str):
    service = UnifiedDataCollectionService()
    return await service.collect_system_metrics(device_id)
```

**Why This Matters**: Centralized SSH management ensures consistent connection pooling, error handling, and resource cleanup.

### 4. PreToolUse: Timezone-Naive Datetime Prevention

**Purpose**: Prevents creation of timezone-naive datetime objects that cause localization issues.

**Trigger**: Activated on `Write` and `Edit` tool operations

**Detection Pattern**: Regex pattern that matches `datetime.now()` without timezone parameter

**Blocked Code**: `datetime.now()` calls without explicit timezone

**Correct Patterns**:
```python
# ❌ BLOCKED - Timezone-naive datetime
from datetime import datetime
timestamp = datetime.now()

# ✅ ALLOWED - Explicit UTC timezone
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)

# ✅ ALLOWED - SQLAlchemy function for database timestamps
from sqlalchemy import func
created_at = Column(DateTime, default=func.now())
```

**Why This Matters**: Timezone-naive datetimes cause issues in distributed systems and databases with different timezone configurations.

### 5. PreToolUse: Non-Idempotent SQL Prevention

**Purpose**: Prevents SQL operations that aren't idempotent and could fail on repeated execution.

**Trigger**: Activated on `Write` and `Edit` tool operations

**Detection Pattern**: Regex patterns for SQL operations without safety checks

**Blocked Code**: `CREATE TABLE`, `INSERT INTO`, `UPDATE SET` without idempotency measures

**Correct Patterns**:
```python
# ❌ BLOCKED - Non-idempotent SQL
CREATE TABLE devices (id INTEGER PRIMARY KEY);
INSERT INTO devices (name) VALUES ('server1');
UPDATE devices SET active = true;

# ✅ ALLOWED - Idempotent SQL operations
CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY);
INSERT INTO devices (name) VALUES ('server1') ON CONFLICT DO NOTHING;
UPDATE devices SET active = true WHERE name = 'server1';
```

**Why This Matters**: Idempotent SQL operations prevent failures during migrations, retries, and parallel execution scenarios.

### 6. PreToolUse: Multiple Connection Pool Prevention

**Purpose**: Prevents creation of multiple database connection pools that waste resources.

**Trigger**: Activated on `Write` and `Edit` tool operations

**Detection Pattern**: Regex pattern that matches connection pool or engine creation

**Blocked Code**: Direct calls to `ConnectionPool()` or `create_engine()`

**Correct Patterns**:
```python
# ❌ BLOCKED - Multiple connection pool creation
from sqlalchemy import create_engine, ConnectionPool
engine = create_engine(DATABASE_URL)
pool = ConnectionPool()

# ✅ ALLOWED - Use shared database instance
from src.core.database import get_db_session

async def get_device_data():
    async with get_db_session() as session:
        return await session.execute(select(Device))
```

**Why This Matters**: Multiple connection pools exhaust database connections and create resource leaks in high-traffic applications.

### 7. PreToolUse: Hardcoded Timeout/Retry Prevention

**Purpose**: Prevents hardcoded timeout and retry values that can't be configured per environment.

**Trigger**: Activated on `Write` and `Edit` tool operations

**Detection Pattern**: Regex pattern that matches hardcoded timeout/retry assignments

**Blocked Code**: Hardcoded values for `timeout=`, `retries=`, `max_attempts=`

**Correct Patterns**:
```python
# ❌ BLOCKED - Hardcoded timeout values
response = await client.get(url, timeout=30)
await retry_operation(max_attempts=3)

# ✅ ALLOWED - Configuration-driven values
from src.core.config import settings
response = await client.get(url, timeout=settings.SSH_CONNECTION_TIMEOUT)
await retry_operation(max_attempts=settings.MAX_RETRY_ATTEMPTS)
```

**Why This Matters**: Hardcoded timeouts prevent proper tuning for different environments and network conditions.

### 8. PreToolUse: Missing Correlation ID Prevention

**Purpose**: Prevents logging without correlation IDs that makes distributed tracing difficult.

**Trigger**: Activated on `Write` and `Edit` tool operations for substantial logging code

**Detection Pattern**: Regex pattern that matches logger calls without correlation_id context

**Blocked Code**: Logger calls in substantial code without correlation ID context

**Correct Patterns**:
```python
# ❌ BLOCKED - Logging without correlation ID (in substantial code blocks)
logger.info("Processing device data")
logger.error("Failed to connect to device")

# ✅ ALLOWED - Structured logging with correlation ID
import structlog
from structlog.contextvars import bind_contextvars

bind_contextvars(correlation_id=request_id, device_id=device.id)
logger = structlog.get_logger()
logger.info("Processing device data", operation="data_collection")
```

**Why This Matters**: Correlation IDs are essential for tracing requests across microservices and debugging distributed system issues.

### 9. PreToolUse: Exception Chaining Enforcement

**Purpose**: Ensures proper exception chaining using `from e` to preserve error context.

**Trigger**: Activated on `Edit` tool operations

**Detection Pattern**: Regex pattern that matches raise statements without exception chaining

**Blocked Code**: Exception raising without proper `from e` chaining

**Correct Patterns**:
```python
# ✅ ALLOWED - Proper exception chaining
try:
    risky_operation()
except Exception as e:
    raise ValueError("Something went wrong") from e  # Preserves original error

# ✅ ALLOWED - Simple re-raise
try:
    risky_operation()
except Exception:
    raise  # Re-raises original exception

# ✅ ALLOWED - New exceptions without chaining context
if not valid_input:
    raise ValueError("Invalid input")  # No previous exception to chain
```

**Why This Matters**: Exception chaining preserves the full error traceback, making debugging much easier by showing both the immediate cause and the root cause.

### 10. PostToolUse: Automatic Code Formatting

**Purpose**: Automatically formats Python files using `ruff` after any file modifications.

**Trigger**: Activated on `Write` and `Edit` tool operations for `.py` files

**Actions**:
- Runs `uv run ruff format <file_path>` on modified Python files
- Applies consistent code formatting across the project
- Removes trailing whitespace and fixes spacing issues

**Example**:
```python
# Before (badly formatted)
def badly_formatted_function(   ):
    x=1+2   
    y = 3 +    4
    return x,y   

# After (auto-formatted by hook)
def badly_formatted_function():
    x = 1 + 2
    y = 3 + 4
    return x, y
```

## Hook Implementation Details

### Decision Control Format

Our hooks use Claude Code's proper decision control format with JSON output that includes permission decisions and reasons for blocking operations.

### Hook Events

- **PreToolUse**: Runs before tool execution, can block operations
- **PostToolUse**: Runs after successful tool execution, performs cleanup/formatting

## Best Practices for Developers

### SQLAlchemy Models

Always use `server_default` for mutable types in database-first architecture:

```python
class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    
    # ✅ Correct: Use server_default for JSONB
    device_metadata = Column(JSONB, server_default='{}')
    tags = Column(JSONB, server_default='[]')
    
    # ✅ Correct: Immutable defaults are fine
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
```

### Exception Handling

Always preserve error context with proper chaining:

```python
async def get_device_info(device_id: str) -> DeviceInfo:
    try:
        result = await ssh_client.execute_command(device_id, "system info")
        return parse_device_info(result)
    except SSHConnectionError as e:
        raise DeviceConnectionError(f"Failed to connect to device {device_id}") from e
    except ParseError as e:
        raise DeviceInfoError(f"Failed to parse device info for {device_id}") from e
```

### Code Formatting

The PostToolUse hook automatically handles formatting, but you can also run manually:

```bash
# Format all Python files
uv run ruff format src/

# Format specific file
uv run ruff format src/models/device.py
```

## Troubleshooting

### Hook Not Triggering

1. Restart Claude Code after making changes to `.claude/settings.json`
2. Check that the file pattern matches (e.g., `.py` extension for formatting)
3. Verify the regex patterns are correctly escaped in JSON

### Hook Errors

If hooks fail with JSON parsing errors:
1. Check the command syntax in the settings file
2. Test the Python command independently
3. Ensure proper JSON escaping for quotes and backslashes

### Debugging Hooks

Add debugging output to hook commands to see what content is being processed.

## Integration with Development Workflow

These hooks integrate seamlessly with:
- **PR Reviews**: Prevent issues before they reach code review stage
- **CI/CD Pipeline**: Complement automated testing and linting
- **Development Environment**: Immediate feedback on code quality issues
- **Code Quality Standards**: Enforce project-wide best practices

## Testing Hooks

To verify hooks are working correctly, attempt to create files with patterns that should be blocked:

**Expected Hook Behavior:**
- **Deprecated Type Annotations**: Blocks old typing module imports, suggests modern alternatives
- **Direct SSH Usage**: Prevents direct SSH client creation, redirects to service layer
- **Timezone Issues**: Catches naive datetime usage, requires explicit UTC timezone
- **SQL Safety**: Prevents non-idempotent operations, enforces safety patterns
- **Resource Management**: Blocks multiple connection pools, enforces shared resources
- **Configuration**: Prevents hardcoded values, requires configuration-driven approach
- **Observability**: Ensures correlation IDs in substantial logging code

**Verification**: Working hooks display error messages starting with "❌" and prevent problematic code from being written to files.

## Future Enhancements

Potential additions to the hook system:
- **Import Organization**: Enforce import ordering standards (isort integration)
- **Security Patterns**: Block potential security vulnerabilities
- **Resource Cleanup**: Ensure proper async context managers and cleanup
- **Performance Patterns**: Detect N+1 queries and inefficient operations
- **API Standards**: Enforce consistent FastAPI endpoint patterns
- **Documentation**: Require docstrings for public functions and classes

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main project development guide
- [MCP_RESOURCES_SUMMARY.md](MCP_RESOURCES_SUMMARY.md) - MCP server resources
- [Claude Code Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) - Official hook reference

---

*This comprehensive hook configuration implements automated prevention of the most common code quality issues in Python infrastructure projects, ensuring consistent code quality, proper architecture patterns, and maintainable codebase practices across the Infrastructor project.*
# Code Cleanup Report - Infrastructor Project

## Executive Summary
Systematic analysis of the codebase reveals significant opportunities for code cleanup and optimization:
- **1,535 unused imports** across the codebase
- **404 generic exception handlers** that could be more specific
- **205 duplicate error logging patterns**
- **216 logger.info statements** (many redundant)
- Extensive code duplication in data collection patterns
- Redundant device query patterns across 25+ locations

## 1. Unused Imports (HIGH PRIORITY)
**Issue**: 1,535 unused imports detected by ruff
**Impact**: Cluttered code, slower imports, maintenance burden

### Most Common Unused Imports:
- `typing.List, Dict, Union` - Should use built-in generics (`list`, `dict`, `|`)
- `uuid.UUID` - Imported but not used in many files
- `fastapi.Depends` - Imported unnecessarily in some API files

### Affected Files Sample:
```
apps/backend/src/api/containers.py - List, UUID unused
apps/backend/src/api/proxy.py - Depends unused
```

**Recommendation**: Run `uv run ruff check --fix --select F401` to auto-remove unused imports

## 2. Duplicate Code Patterns

### A. Collection Method Pattern (10+ duplicates)
Every API endpoint and MCP tool has nearly identical collection method setup:

```python
# Pattern repeated in containers.py, devices.py, vms.py, system_monitoring.py, etc.
async def collect_something():
    from apps.backend.src.utils.ssh_client import execute_ssh_command_simple
    result = await execute_ssh_command_simple(hostname, cmd, timeout)
    if not result.success:
        raise DataCollectionError(...)
    # Parse and return data
```

**Recommendation**: Create a base collection class or decorator

### B. Device Query Pattern (25+ duplicates)
Same device lookup logic repeated everywhere:

```python
# Repeated in 25+ locations
query = select(Device).where(Device.hostname == hostname)
result = await session.execute(query)
device = result.scalar_one_or_none()
if not device:
    raise DeviceNotFoundError(hostname)
```

**Recommendation**: Centralize in DeviceService.get_device_by_hostname()

### C. Exception Handling Pattern (404 duplicates)
Generic exception handling with identical logging:

```python
except Exception as e:
    logger.error(f"Error doing X: {e}")
    raise HTTPException(status_code=500, detail=f"Failed: {str(e)}") from e
```

**Recommendation**: Create exception middleware or decorator

## 3. Redundant Logging

### Duplicate Log Messages:
- 9 different "Starting..." messages that are nearly identical
- 205 instances of `logger.error(...Error...{e})` pattern
- Multiple levels logging the same information

### Examples:
```python
# In unified_data_collection.py
logger.info(f"Starting universal data collection: type={data_type}...")
# Later in same function
logger.info(f"Successfully collected fresh data: type={data_type}...")
```

**Recommendation**: 
- Use structured logging with consistent format
- Log at entry/exit points only, not every step
- Remove redundant "Starting..." logs

## 4. Stale/Deprecated Code

### Deprecated Type Hints:
Files still using old typing imports instead of Python 3.11+ built-ins:
- `from typing import List, Dict, Optional, Union`
- Should use: `list`, `dict`, `str | None`, etc.

### Unused Service Methods:
Several service classes have methods that aren't called anywhere:
- Check metrics_service.py for unused aggregation methods
- Review container_service.py for redundant container operations

## 5. Configuration & Setup Redundancy

### Main.py Lifespan Function:
- Duplicate SWAG and Docker monitoring setup code (lines 231-407)
- Both functions follow identical patterns with minor variations

**Recommendation**: Refactor into single configurable setup function

### Database Session Handling:
- 175 instances of session management code
- Each creates session, executes query, handles errors identically

**Recommendation**: Use context manager or repository pattern

## 6. Specific Files Needing Cleanup

### High Priority Files:
1. **apps/backend/src/api/containers.py**
   - 4 duplicate collection methods
   - Unused imports (List, UUID)
   - Repetitive exception handling

2. **apps/backend/src/mcp/tools/system_monitoring.py**
   - 4 nearly identical collect_ functions
   - Could be refactored to single parameterized method

3. **apps/backend/src/main.py**
   - Duplicate monitoring setup code (SWAG vs Docker)
   - Could be 100+ lines shorter

4. **apps/backend/src/services/polling_service.py**
   - Massive file with repeated patterns
   - Each poll method follows same structure

## 7. Quick Wins

### Immediate Actions (< 1 hour):
1. Run `uv run ruff check --fix --select F401` to remove unused imports
2. Delete commented-out code blocks
3. Remove redundant "Starting..." log messages

### Short-term Actions (< 1 day):
1. Create `@handle_api_errors` decorator for consistent error handling
2. Centralize device lookup in DeviceService
3. Create base CollectionMethod class

### Long-term Refactoring:
1. Implement repository pattern for database operations
2. Refactor polling service into smaller, focused modules
3. Create structured logging system

## 8. Metrics Summary

| Issue Type | Count | Priority | Effort |
|------------|-------|----------|--------|
| Unused Imports | 1,535 | HIGH | Low (automated) |
| Generic Exception Handlers | 404 | MEDIUM | Medium |
| Duplicate Error Logs | 205 | LOW | Low |
| Duplicate Device Queries | 25+ | HIGH | Medium |
| Collection Method Duplicates | 10+ | HIGH | High |
| Deprecated Type Hints | Many | MEDIUM | Low (automated) |

## 9. Estimated Impact

### If all recommendations implemented:
- **Code reduction**: ~2,000-3,000 lines (15-20% of codebase)
- **Import time**: 10-15% faster
- **Maintenance**: Significantly easier
- **Bug surface**: Reduced by eliminating duplication
- **Testing**: Easier with centralized logic

## 10. Recommended Execution Plan

### Phase 1: Automated Cleanup (Week 1)
- Remove unused imports
- Update deprecated type hints
- Remove commented code

### Phase 2: Centralization (Week 2)
- Centralize device queries
- Create error handling decorator
- Consolidate logging patterns

### Phase 3: Refactoring (Week 3-4)
- Refactor collection methods
- Simplify main.py lifespan
- Break up large service files

### Phase 4: Testing & Documentation (Week 5)
- Update tests for refactored code
- Document new patterns
- Create developer guidelines

---

*Generated: 2025-08-07*
*Total Files Analyzed: 100+*
*Lines of Code: ~15,000*
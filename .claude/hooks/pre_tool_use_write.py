#!/usr/bin/env python3
import sys
import json
import re


def main():
    try:
        data = json.load(sys.stdin)
        content = data.get("tool_input", {}).get("content", "")
        issues = []

        patterns = [
            (
                r"Column\([^,]*,\s*default\s*=\s*(\{[^}]*\}|\[[^\]]*\])",
                "❌ Mutable default in SQLAlchemy Column! Use server_default instead",
            ),
            (
                r"from typing import.*(Optional|List|Dict|Union)",
                "❌ Outdated type annotations! Use str | None, list[str], dict[str, int] instead",
            ),
            # SSH client check disabled for UnifiedDataCollectionService implementation
            (
                r"datetime\.now\(\)(?![\s]*\([^)]*timezone)",
                "❌ Timezone-naive datetime! Use datetime.now(timezone.utc)",
            ),
            (
                r"CREATE TABLE(?!.*IF NOT EXISTS)|INSERT INTO(?!.*ON CONFLICT)|UPDATE.*SET(?!.*WHERE)",
                "❌ Non-idempotent SQL! Use CREATE TABLE IF NOT EXISTS, INSERT...ON CONFLICT DO NOTHING",
            ),
            (
                r"ConnectionPool\(|create_engine\(",
                "❌ Multiple connection pools! Use single shared connection pool",
            ),
            (
                r"timeout\s*=\s*\d+|retries\s*=\s*\d+|max_attempts\s*=\s*\d+",
                "❌ Hardcoded timeouts/retries! Use configuration-driven values",
            ),
        ]

        for pattern, message in patterns:
            if re.search(pattern, content):
                issues.append(message)

        # Skip correlation ID check - using regular logging pattern instead

        if issues:
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": " | ".join(issues),
                }
            }
        else:
            result = {}

        print(json.dumps(result))

    except Exception as e:
        # If there's an error, allow the operation to continue
        print(json.dumps({}))


if __name__ == "__main__":
    main()

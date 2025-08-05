#!/usr/bin/env python3
import sys
import json
import re


def main():
    try:
        data = json.load(sys.stdin)
        content = data.get("tool_input", {}).get("new_string", "")
        issues = []

        patterns = [
            (
                r"except\s+\w+.*?raise\s+\w+\([^)]*\)(?!.*from)",
                "❌ Missing exception chaining! Use raise Exception() from e",
            ),
            (
                r"from typing import.*(Optional|List|Dict|Union)",
                "❌ Outdated type annotations! Use Python 3.11+ built-in types",
            ),
            (
                r"get_ssh_client\(\)|SSHClient\(\)",
                "❌ Direct SSH client creation! Use UnifiedDataCollectionService",
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

        # Special case for correlation ID check (only for substantial code)
        if "logger." in content and "correlation_id" not in content and len(content) > 100:
            issues.append(
                "❌ Missing correlation ID! Use structlog.contextvars for request tracing"
            )

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

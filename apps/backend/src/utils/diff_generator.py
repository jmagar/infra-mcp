"""
Diff Generator Utility

Provides comprehensive diff generation and analysis for configuration files.
Supports multiple diff formats and statistical analysis of changes.
"""

import difflib
import json
import re
from typing import Any


class DiffGenerator:
    """
    Utility class for generating diffs between configuration content.

    Supports unified diff, side-by-side diff, and JSON diff formats
    with comprehensive statistical analysis of changes.
    """

    def generate_unified_diff(
        self,
        old_content: str,
        new_content: str,
        old_name: str = "old",
        new_name: str = "new",
        context_lines: int = 3,
    ) -> str:
        """
        Generate a unified diff between two text contents.

        Args:
            old_content: Original content
            new_content: Modified content
            old_name: Name/label for old content
            new_name: Name/label for new content
            context_lines: Number of context lines to include

        Returns:
            Unified diff as string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=old_name,
            tofile=new_name,
            n=context_lines,
        )

        return "".join(diff)

    def generate_side_by_side_diff(
        self,
        old_content: str,
        new_content: str,
        width: int = 80,
    ) -> dict[str, Any]:
        """
        Generate a side-by-side diff visualization.

        Args:
            old_content: Original content
            new_content: Modified content
            width: Maximum width for each side

        Returns:
            Dictionary with side-by-side diff data
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Use difflib.SequenceMatcher for detailed comparison
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        diff_blocks = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Lines are identical
                for k in range(i2 - i1):
                    old_line = old_lines[i1 + k] if i1 + k < len(old_lines) else ""
                    new_line = new_lines[j1 + k] if j1 + k < len(new_lines) else ""
                    diff_blocks.append(
                        {
                            "type": "equal",
                            "old_number": i1 + k + 1,
                            "new_number": j1 + k + 1,
                            "old_content": old_line[:width],
                            "new_content": new_line[:width],
                        }
                    )

            elif tag == "delete":
                # Lines only in old content
                for k in range(i2 - i1):
                    diff_blocks.append(
                        {
                            "type": "delete",
                            "old_number": i1 + k + 1,
                            "new_number": None,
                            "old_content": old_lines[i1 + k][:width],
                            "new_content": "",
                        }
                    )

            elif tag == "insert":
                # Lines only in new content
                for k in range(j2 - j1):
                    diff_blocks.append(
                        {
                            "type": "insert",
                            "old_number": None,
                            "new_number": j1 + k + 1,
                            "old_content": "",
                            "new_content": new_lines[j1 + k][:width],
                        }
                    )

            elif tag == "replace":
                # Lines changed
                max_lines = max(i2 - i1, j2 - j1)
                for k in range(max_lines):
                    old_line = old_lines[i1 + k] if i1 + k < i2 else ""
                    new_line = new_lines[j1 + k] if j1 + k < j2 else ""
                    diff_blocks.append(
                        {
                            "type": "replace",
                            "old_number": i1 + k + 1 if i1 + k < i2 else None,
                            "new_number": j1 + k + 1 if j1 + k < j2 else None,
                            "old_content": old_line[:width],
                            "new_content": new_line[:width],
                        }
                    )

        return {
            "format": "side-by-side",
            "blocks": diff_blocks,
            "statistics": self.get_diff_summary(diff_blocks),
        }

    def generate_json_diff(
        self,
        old_content: str,
        new_content: str,
    ) -> dict[str, Any]:
        """
        Generate a JSON-structured diff for programmatic use.

        Args:
            old_content: Original content
            new_content: Modified content

        Returns:
            JSON-structured diff data
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                change = {
                    "operation": tag,
                    "old_start": i1 + 1,
                    "old_end": i2,
                    "new_start": j1 + 1,
                    "new_end": j2,
                    "old_lines": old_lines[i1:i2],
                    "new_lines": new_lines[j1:j2],
                }
                changes.append(change)

        return {
            "format": "json",
            "changes": changes,
            "statistics": {
                "total_changes": len(changes),
                "lines_added": sum(
                    len(c["new_lines"]) for c in changes if c["operation"] in ["insert", "replace"]
                ),
                "lines_removed": sum(
                    len(c["old_lines"]) for c in changes if c["operation"] in ["delete", "replace"]
                ),
                "lines_modified": sum(1 for c in changes if c["operation"] == "replace"),
            },
        }

    def get_diff_summary(self, diff_content: str | list[dict[str, Any]]) -> dict[str, Any]:
        """
        Generate statistical summary of diff changes.

        Args:
            diff_content: Diff content (unified diff string or side-by-side blocks)

        Returns:
            Statistical summary of changes
        """
        if isinstance(diff_content, str):
            return self._analyze_unified_diff(diff_content)
        elif isinstance(diff_content, list):
            return self._analyze_side_by_side_diff(diff_content)
        else:
            return {
                "lines_added": 0,
                "lines_removed": 0,
                "lines_modified": 0,
                "total_changes": 0,
                "change_ratio": 0.0,
            }

    def _analyze_unified_diff(self, diff_content: str) -> dict[str, Any]:
        """Analyze unified diff format for statistics."""
        lines = diff_content.splitlines()

        lines_added = 0
        lines_removed = 0
        total_lines = 0

        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_removed += 1
            elif (
                not line.startswith("@@")
                and not line.startswith("+++")
                and not line.startswith("---")
            ):
                total_lines += 1

        lines_modified = min(lines_added, lines_removed)
        lines_added = lines_added - lines_modified
        lines_removed = lines_removed - lines_modified

        total_changes = lines_added + lines_removed + lines_modified
        change_ratio = total_changes / max(total_lines, 1) if total_lines > 0 else 0.0

        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "total_changes": total_changes,
            "total_lines": total_lines,
            "change_ratio": change_ratio,
            "change_percentage": change_ratio * 100,
        }

    def _analyze_side_by_side_diff(self, diff_blocks: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze side-by-side diff format for statistics."""
        lines_added = 0
        lines_removed = 0
        lines_modified = 0
        total_lines = len(diff_blocks)

        for block in diff_blocks:
            if block["type"] == "insert":
                lines_added += 1
            elif block["type"] == "delete":
                lines_removed += 1
            elif block["type"] == "replace":
                lines_modified += 1

        total_changes = lines_added + lines_removed + lines_modified
        change_ratio = total_changes / max(total_lines, 1) if total_lines > 0 else 0.0

        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_modified": lines_modified,
            "total_changes": total_changes,
            "total_lines": total_lines,
            "change_ratio": change_ratio,
            "change_percentage": change_ratio * 100,
        }

    def get_change_highlights(
        self,
        old_content: str,
        new_content: str,
        context_lines: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Extract key change highlights from a diff.

        Args:
            old_content: Original content
            new_content: Modified content
            context_lines: Number of context lines around changes

        Returns:
            List of change highlights with context
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        highlights = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                # Get context around the change
                context_start_old = max(0, i1 - context_lines)
                context_end_old = min(len(old_lines), i2 + context_lines)
                context_start_new = max(0, j1 - context_lines)
                context_end_new = min(len(new_lines), j2 + context_lines)

                highlight = {
                    "type": tag,
                    "old_range": {"start": i1 + 1, "end": i2},
                    "new_range": {"start": j1 + 1, "end": j2},
                    "old_context": old_lines[context_start_old:context_end_old],
                    "new_context": new_lines[context_start_new:context_end_new],
                    "changed_lines": {
                        "old": old_lines[i1:i2],
                        "new": new_lines[j1:j2],
                    },
                    "summary": self._generate_change_summary(
                        tag, old_lines[i1:i2], new_lines[j1:j2]
                    ),
                }
                highlights.append(highlight)

        return highlights

    def _generate_change_summary(
        self,
        change_type: str,
        old_lines: list[str],
        new_lines: list[str],
    ) -> str:
        """Generate a human-readable summary of a change."""
        if change_type == "insert":
            return f"Added {len(new_lines)} line(s)"
        elif change_type == "delete":
            return f"Removed {len(old_lines)} line(s)"
        elif change_type == "replace":
            return f"Modified {max(len(old_lines), len(new_lines))} line(s)"
        else:
            return "No change"

    def detect_semantic_changes(
        self,
        old_content: str,
        new_content: str,
        file_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Detect semantic changes based on file type and content patterns.

        Args:
            old_content: Original content
            new_content: Modified content
            file_type: File type hint for semantic analysis

        Returns:
            Semantic change analysis
        """
        semantic_changes = {
            "configuration_sections": self._detect_config_section_changes(old_content, new_content),
            "key_value_changes": self._detect_key_value_changes(old_content, new_content),
            "structural_changes": self._detect_structural_changes(old_content, new_content),
            "security_implications": self._detect_security_changes(old_content, new_content),
        }

        # Add file-type specific analysis
        if file_type:
            if file_type in ["nginx", "apache"]:
                semantic_changes["web_server_changes"] = self._detect_web_server_changes(
                    old_content, new_content
                )
            elif file_type in ["docker-compose", "yaml", "yml"]:
                semantic_changes["service_changes"] = self._detect_service_changes(
                    old_content, new_content
                )
            elif file_type in ["json"]:
                semantic_changes["json_structure_changes"] = self._detect_json_changes(
                    old_content, new_content
                )

        return semantic_changes

    def _detect_config_section_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect changes in configuration sections."""
        # Look for common section patterns like [section], <section>, etc.
        section_patterns = [
            r"^\[([^\]]+)\]",  # INI-style sections
            r"^<([^>]+)>",  # Apache/Nginx style
            r"^(\w+):$",  # YAML sections
        ]

        old_sections = set()
        new_sections = set()

        for pattern in section_patterns:
            old_sections.update(re.findall(pattern, old_content, re.MULTILINE))
            new_sections.update(re.findall(pattern, new_content, re.MULTILINE))

        return {
            "sections_added": list(new_sections - old_sections),
            "sections_removed": list(old_sections - new_sections),
            "sections_common": list(old_sections & new_sections),
        }

    def _detect_key_value_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect key-value pair changes."""
        # Look for key=value, key: value, key value patterns
        kv_patterns = [
            r"^(\w+)\s*[=:]\s*(.+)$",  # key=value or key: value
            r"^(\w+)\s+(.+)$",  # key value (space-separated)
        ]

        old_kvs = {}
        new_kvs = {}

        for pattern in kv_patterns:
            for match in re.finditer(pattern, old_content, re.MULTILINE):
                old_kvs[match.group(1)] = match.group(2)
            for match in re.finditer(pattern, new_content, re.MULTILINE):
                new_kvs[match.group(1)] = match.group(2)

        changed_keys = []
        for key in old_kvs:
            if key in new_kvs and old_kvs[key] != new_kvs[key]:
                changed_keys.append(
                    {
                        "key": key,
                        "old_value": old_kvs[key],
                        "new_value": new_kvs[key],
                    }
                )

        return {
            "keys_added": list(set(new_kvs.keys()) - set(old_kvs.keys())),
            "keys_removed": list(set(old_kvs.keys()) - set(new_kvs.keys())),
            "keys_changed": changed_keys,
        }

    def _detect_structural_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect structural changes like indentation, brackets, etc."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        old_structure = {
            "total_lines": len(old_lines),
            "empty_lines": sum(1 for line in old_lines if not line.strip()),
            "indented_lines": sum(1 for line in old_lines if line.startswith((" ", "\t"))),
            "bracket_lines": sum(1 for line in old_lines if any(c in line for c in "{}[]()'")),
        }

        new_structure = {
            "total_lines": len(new_lines),
            "empty_lines": sum(1 for line in new_lines if not line.strip()),
            "indented_lines": sum(1 for line in new_lines if line.startswith((" ", "\t"))),
            "bracket_lines": sum(1 for line in new_lines if any(c in line for c in "{}[]()'")),
        }

        return {
            "line_count_change": new_structure["total_lines"] - old_structure["total_lines"],
            "indentation_change": new_structure["indented_lines"] - old_structure["indented_lines"],
            "structure_complexity_change": new_structure["bracket_lines"]
            - old_structure["bracket_lines"],
        }

    def _detect_security_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect potential security-related changes."""
        security_keywords = [
            "password",
            "passwd",
            "secret",
            "key",
            "token",
            "auth",
            "ssl",
            "tls",
            "cert",
            "https",
            "encryption",
            "hash",
            "firewall",
            "port",
            "access",
            "permission",
            "user",
            "admin",
        ]

        old_security_lines = []
        new_security_lines = []

        for i, line in enumerate(old_content.splitlines()):
            if any(keyword in line.lower() for keyword in security_keywords):
                old_security_lines.append((i + 1, line))

        for i, line in enumerate(new_content.splitlines()):
            if any(keyword in line.lower() for keyword in security_keywords):
                new_security_lines.append((i + 1, line))

        return {
            "security_related_changes": len(new_security_lines) != len(old_security_lines),
            "old_security_lines": len(old_security_lines),
            "new_security_lines": len(new_security_lines),
            "potential_risk_level": "high"
            if abs(len(new_security_lines) - len(old_security_lines)) > 2
            else "medium"
            if len(new_security_lines) != len(old_security_lines)
            else "low",
        }

    def _detect_web_server_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect web server specific changes."""
        # Look for common web server directives
        web_patterns = {
            "server_blocks": r"server\s*{",
            "location_blocks": r"location\s+[^{]+{",
            "listen_directives": r"listen\s+\d+",
            "proxy_directives": r"proxy_\w+",
            "ssl_directives": r"ssl_\w+",
        }

        changes = {}
        for name, pattern in web_patterns.items():
            old_matches = len(re.findall(pattern, old_content, re.IGNORECASE))
            new_matches = len(re.findall(pattern, new_content, re.IGNORECASE))
            changes[name] = new_matches - old_matches

        return changes

    def _detect_service_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect service/container changes in docker-compose or similar files."""
        # Look for service definitions and key properties
        service_patterns = {
            "services": r"^\s*\w+:",
            "images": r"image:\s*(.+)",
            "ports": r"ports:",
            "volumes": r"volumes:",
            "environment": r"environment:",
        }

        changes = {}
        for name, pattern in service_patterns.items():
            old_matches = len(re.findall(pattern, old_content, re.MULTILINE))
            new_matches = len(re.findall(pattern, new_content, re.MULTILINE))
            changes[name] = new_matches - old_matches

        return changes

    def _detect_json_changes(self, old_content: str, new_content: str) -> dict[str, Any]:
        """Detect JSON structure changes."""
        try:
            old_json = json.loads(old_content)
            new_json = json.loads(new_content)

            def count_keys(obj, depth=0):
                if isinstance(obj, dict):
                    return sum(1 + count_keys(v, depth + 1) for v in obj.values())
                elif isinstance(obj, list):
                    return sum(count_keys(item, depth + 1) for item in obj)
                return 0

            return {
                "old_key_count": count_keys(old_json),
                "new_key_count": count_keys(new_json),
                "structure_complexity_change": count_keys(new_json) - count_keys(old_json),
                "valid_json": True,
            }
        except json.JSONDecodeError:
            return {
                "valid_json": False,
                "structure_complexity_change": 0,
            }

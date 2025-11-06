"""Markdown utilities for formatting Linear issue references.

This module provides utilities for post-processing text to add clickable
Markdown links for Linear issue identifiers.
"""

import re
from typing import Dict


def add_clickable_issue_links(text: str, issue_map: Dict[str, str]) -> str:
    """
    Post-process text to add clickable Markdown links for issue identifiers.

    This function uses a two-pass approach:
    1. First pass: Convert plain issue IDs to bold (LDRS-63 -> **LDRS-63**)
    2. Second pass: Convert bold IDs to clickable links (**LDRS-63** -> [**LDRS-63**](url))

    This is done AFTER Claude generates text because Claude tends to remove
    or modify Markdown links during generation and may not consistently use bold.

    Handles various formats:
    - LDRS-63 -> [**LDRS-63**](url)
    - **ISSUE-123** -> [**ISSUE-123**](url)
    - **🚨 ISSUE-123** -> [**🚨 ISSUE-123**](url)
    - ISSUE-123: -> [**ISSUE-123**](url):
    - **ISSUE-123:** -> [**ISSUE-123:**](url)

    Args:
        text: Text containing issue identifiers like DMD-480 or **DMD-480**
        issue_map: Mapping of identifier -> URL (e.g., {"DMD-480": "https://..."})

    Returns:
        Text with clickable Markdown links for issue identifiers

    Example:
        >>> issue_map = {"DMD-480": "https://linear.app/keboola/issue/DMD-480"}
        >>> text = "DMD-480: Fix authentication bug"
        >>> add_clickable_issue_links(text, issue_map)
        '[**DMD-480**](https://linear.app/keboola/issue/DMD-480): Fix authentication bug'
    """
    if not issue_map:
        return text

    # PASS 1: Make all plain issue IDs bold (if not already)
    # Match: ISSUE-123 but not **ISSUE-123** or [**ISSUE-123**] or inside URLs
    # Negative lookbehind: (?<!\*\*) - not preceded by **
    # Negative lookbehind: (?<!\[) - not preceded by [
    # Negative lookbehind: (?<!/) - not preceded by / (inside URL)
    # Word boundary: \b - ensures proper word start/end
    # Negative lookahead: (?!\*\*) - not followed by **
    # Negative lookahead: (?!\]\() - not followed by ]( (inside link)
    text = re.sub(
        r"(?<!\*\*)(?<!\[)(?<!/)\b([A-Z][A-Z0-9]+-\d+)\b(?!\*\*)(?!\]\()",
        r"**\1**",
        text,
    )

    # PASS 2: Convert bold IDs to clickable links (but not if already linked)

    def replace_identifier(match):
        prefix = match.group(1) or ""  # e.g., "🚨 " or ""
        identifier = match.group(2)  # e.g., "DMD-480"
        colon_inside = match.group(3) or ""  # Colon inside **
        colon_outside = match.group(4) or ""  # Colon outside **

        if identifier in issue_map:
            url = issue_map[identifier]
            # Create clickable link, preserving emoji prefix and colons
            return f"[**{prefix}{identifier}{colon_inside}**]({url}){colon_outside}"
        else:
            return match.group(0)  # No URL available, keep original

    # Match **[PREFIX] IDENTIFIER[:][**][:] with optional prefix (emoji, icons, etc.)
    # But ONLY if not already part of a Markdown link: [**...**](url)
    # Pattern handles:
    # - **DMD-480**          -> plain
    # - **🚨 DMD-480**       -> with emoji prefix
    # - **DMD-480**:         -> colon outside
    # - **DMD-480:**         -> colon inside
    # Group 1: optional prefix (emoji + space, or other non-alphanumeric chars + space)
    # Group 2: identifier (DMD-480)
    # Group 3: optional colon inside **
    # Group 4: optional colon outside **
    # Negative lookbehind: (?<!\[) - not preceded by [ (inside link)
    pattern = r"(?<!\[)\*\*((?:[^\*\w]*\s+)?)([A-Z][A-Z0-9]+-\d+)(:?)\*\*(:?)(?!\]\()"
    text_with_links = re.sub(pattern, replace_identifier, text)

    return text_with_links

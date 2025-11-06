"""Unit tests for Markdown utilities."""

import pytest
from linear_chief.utils.markdown import add_clickable_issue_links


class TestAddClickableIssueLinks:
    """Test suite for add_clickable_issue_links function."""

    @pytest.fixture
    def issue_map(self):
        """Sample issue map for testing."""
        return {
            "DMD-480": "https://linear.app/keboola/issue/DMD-480",
            "LDRS-63": "https://linear.app/company/issue/LDRS-63",
            "PROJ-123": "https://linear.app/org/issue/PROJ-123",
        }

    def test_plain_issue_id_gets_bolded_and_linked(self, issue_map):
        """Test that plain issue ID gets bold and linked."""
        text = "LDRS-63: R&D on how ai first mindset changes techniques"
        result = add_clickable_issue_links(text, issue_map)
        expected = "[**LDRS-63**](https://linear.app/company/issue/LDRS-63): R&D on how ai first mindset changes techniques"
        assert result == expected

    def test_plain_issue_id_in_list(self, issue_map):
        """Test plain issue ID in a list item."""
        text = "- LDRS-63: R&D on how ai first mindset\n- DMD-480: Fix bug"
        result = add_clickable_issue_links(text, issue_map)
        assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result

    def test_already_bold_issue_id(self, issue_map):
        """Test that already bold issue IDs get linked."""
        text = "**DMD-480**: Fix authentication bug"
        result = add_clickable_issue_links(text, issue_map)
        expected = "[**DMD-480**](https://linear.app/keboola/issue/DMD-480): Fix authentication bug"
        assert result == expected

    def test_bold_with_emoji_prefix(self, issue_map):
        """Test bold issue ID with emoji prefix."""
        text = "**🚨 DMD-480**: Critical bug"
        result = add_clickable_issue_links(text, issue_map)
        expected = "[**🚨 DMD-480**](https://linear.app/keboola/issue/DMD-480): Critical bug"
        assert result == expected

    def test_plain_with_colon_inside_sentence(self, issue_map):
        """Test plain issue ID with colon in middle of sentence."""
        text = "Check PROJ-123: the authentication is broken"
        result = add_clickable_issue_links(text, issue_map)
        assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123):" in result

    def test_multiple_issue_ids_in_text(self, issue_map):
        """Test multiple issue IDs in same text."""
        text = "Work on DMD-480 and LDRS-63 today, also check PROJ-123"
        result = add_clickable_issue_links(text, issue_map)
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
        assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
        assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in result

    def test_issue_id_at_start_of_line(self, issue_map):
        """Test issue ID at start of line."""
        text = "DMD-480 is the first priority"
        result = add_clickable_issue_links(text, issue_map)
        assert result.startswith("[**DMD-480**](https://linear.app/keboola/issue/DMD-480)")

    def test_issue_id_at_end_of_line(self, issue_map):
        """Test issue ID at end of line."""
        text = "Please review DMD-480"
        result = add_clickable_issue_links(text, issue_map)
        assert result.endswith("[**DMD-480**](https://linear.app/keboola/issue/DMD-480)")

    def test_issue_id_without_url_in_map(self, issue_map):
        """Test issue ID that's not in the map stays unchanged (but gets bolded)."""
        text = "Unknown issue: UNKNOWN-999"
        result = add_clickable_issue_links(text, issue_map)
        # Should be bolded but NOT linked
        assert "**UNKNOWN-999**" in result
        assert "[**UNKNOWN-999**]" not in result

    def test_empty_issue_map(self):
        """Test with empty issue map returns original text."""
        text = "DMD-480: Fix bug"
        result = add_clickable_issue_links(text, {})
        assert result == text

    def test_no_issue_ids_in_text(self, issue_map):
        """Test text without any issue IDs."""
        text = "This is a normal sentence without any issues."
        result = add_clickable_issue_links(text, issue_map)
        assert result == text

    def test_already_linked_issue_id(self, issue_map):
        """Test that already linked issue IDs are not double-processed."""
        text = "[**DMD-480**](https://linear.app/keboola/issue/DMD-480): Already linked"
        result = add_clickable_issue_links(text, issue_map)
        # Should remain unchanged (negative lookbehind prevents re-matching)
        assert result == text

    def test_issue_id_in_markdown_code_block(self, issue_map):
        """Test that issue IDs in code blocks get processed (Markdown doesn't escape them)."""
        # Note: This is expected behavior - Markdown inline code doesn't use [] so it will match
        text = "Run `git commit -m 'Fix DMD-480'`"
        result = add_clickable_issue_links(text, issue_map)
        # This WILL be converted because backticks don't prevent regex matching
        assert "[**DMD-480**]" in result

    def test_conversation_response_format(self, issue_map):
        """Test realistic conversation response format from Claude."""
        text = """Here are your high-priority issues:

- LDRS-63: R&D on how ai first mindset changes techniques
- DMD-480: Fix authentication bug
- PROJ-123: Implement new feature

You should focus on LDRS-63 first as it's blocking other work."""
        result = add_clickable_issue_links(text, issue_map)

        # All three issue IDs should be linked
        assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
        assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in result

    def test_briefing_format_with_bold(self, issue_map):
        """Test briefing format where issues are already bold."""
        text = """**🚨 Critical Issues:**

1. **DMD-480**: Authentication system down
2. **LDRS-63**: Research blocking deployment"""
        result = add_clickable_issue_links(text, issue_map)

        # Should handle bold IDs with emoji prefix
        assert "[**🚨 Critical Issues:**]" not in result  # Should NOT link section headers
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
        assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result

    def test_mixed_bold_and_plain(self, issue_map):
        """Test mix of bold and plain issue IDs."""
        text = "**DMD-480** is related to LDRS-63 and PROJ-123"
        result = add_clickable_issue_links(text, issue_map)

        # All should be linked
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
        assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
        assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in result

    def test_issue_id_with_numbers_in_prefix(self, issue_map):
        """Test issue IDs with numbers in team prefix."""
        issue_map_numeric = {"ABC123-456": "https://linear.app/test/issue/ABC123-456"}
        text = "Issue ABC123-456 needs attention"
        result = add_clickable_issue_links(text, issue_map_numeric)
        assert "[**ABC123-456**](https://linear.app/test/issue/ABC123-456)" in result

    def test_issue_id_case_sensitive(self, issue_map):
        """Test that issue IDs are case-sensitive (must start with uppercase)."""
        text = "dmd-480 is not a valid issue ID, but DMD-480 is"
        result = add_clickable_issue_links(text, issue_map)

        # Lowercase version should NOT be matched
        assert "dmd-480" in result
        assert "[**dmd-480**]" not in result

        # Uppercase version SHOULD be matched
        assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result

    def test_preserve_colon_placement(self, issue_map):
        """Test that colons are preserved in correct positions."""
        text1 = "**DMD-480**: With colon outside"
        text2 = "**DMD-480:** With colon inside"

        result1 = add_clickable_issue_links(text1, issue_map)
        result2 = add_clickable_issue_links(text2, issue_map)

        # Both should work and preserve colon position
        assert result1 == "[**DMD-480**](https://linear.app/keboola/issue/DMD-480): With colon outside"
        assert result2 == "[**DMD-480:**](https://linear.app/keboola/issue/DMD-480) With colon inside"

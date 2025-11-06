#!/usr/bin/env python3
"""Manual test script to demonstrate clickable issue links fix.

This script demonstrates the fix for issue links in conversation responses.

Before fix:
    - LDRS-63: R&D on how ai first mindset changes techniques

After fix:
    [**LDRS-63**](https://linear.app/company/issue/LDRS-63): R&D on how ai first mindset changes techniques
"""

from linear_chief.utils.markdown import add_clickable_issue_links


def test_plain_text_scenario():
    """Test the exact scenario from the user's screenshot."""
    print("=" * 80)
    print("TEST 1: Plain text issue IDs (from user screenshot)")
    print("=" * 80)

    # This is what Claude returns in conversation responses
    response_text = """Here are your high-priority issues:

- LDRS-63: R&D on how ai first mindset changes techniques
- DMD-480: Fix authentication bug
- PROJ-123: Implement new feature

You should focus on LDRS-63 first as it's blocking other work."""

    issue_map = {
        "LDRS-63": "https://linear.app/company/issue/LDRS-63",
        "DMD-480": "https://linear.app/keboola/issue/DMD-480",
        "PROJ-123": "https://linear.app/org/issue/PROJ-123",
    }

    print("\nBEFORE (plain text):")
    print("-" * 80)
    print(response_text)

    result = add_clickable_issue_links(response_text, issue_map)

    print("\nAFTER (clickable links):")
    print("-" * 80)
    print(result)

    # Verify all links were added
    assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
    assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
    assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in result

    print("\n✅ SUCCESS: All issue IDs converted to clickable links!")


def test_already_bold_scenario():
    """Test briefing format where issue IDs are already bold."""
    print("\n" + "=" * 80)
    print("TEST 2: Already bold issue IDs (briefing format)")
    print("=" * 80)

    # This is what briefing agent returns
    briefing_text = """**🚨 Critical Issues:**

1. **DMD-480**: Authentication system down
2. **LDRS-63**: Research blocking deployment"""

    issue_map = {
        "LDRS-63": "https://linear.app/company/issue/LDRS-63",
        "DMD-480": "https://linear.app/keboola/issue/DMD-480",
    }

    print("\nBEFORE (bold but not linked):")
    print("-" * 80)
    print(briefing_text)

    result = add_clickable_issue_links(briefing_text, issue_map)

    print("\nAFTER (clickable links):")
    print("-" * 80)
    print(result)

    # Verify links were added
    assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
    assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result

    print("\n✅ SUCCESS: Bold issue IDs converted to clickable links!")


def test_mixed_scenario():
    """Test mix of plain and bold issue IDs."""
    print("\n" + "=" * 80)
    print("TEST 3: Mixed plain and bold issue IDs")
    print("=" * 80)

    text = "**DMD-480** is related to LDRS-63 and mentioned in PROJ-123"

    issue_map = {
        "LDRS-63": "https://linear.app/company/issue/LDRS-63",
        "DMD-480": "https://linear.app/keboola/issue/DMD-480",
        "PROJ-123": "https://linear.app/org/issue/PROJ-123",
    }

    print("\nBEFORE:")
    print("-" * 80)
    print(text)

    result = add_clickable_issue_links(text, issue_map)

    print("\nAFTER:")
    print("-" * 80)
    print(result)

    # Verify all links were added
    assert "[**DMD-480**](https://linear.app/keboola/issue/DMD-480)" in result
    assert "[**LDRS-63**](https://linear.app/company/issue/LDRS-63)" in result
    assert "[**PROJ-123**](https://linear.app/org/issue/PROJ-123)" in result

    print("\n✅ SUCCESS: All issue IDs (both plain and bold) converted to clickable links!")


def test_already_linked_scenario():
    """Test that already linked issue IDs are not double-processed."""
    print("\n" + "=" * 80)
    print("TEST 4: Already linked issue IDs (should not be modified)")
    print("=" * 80)

    # This is already a properly formatted link
    text = "[**DMD-480**](https://linear.app/keboola/issue/DMD-480): Already linked"

    issue_map = {
        "DMD-480": "https://linear.app/keboola/issue/DMD-480",
    }

    print("\nBEFORE (already linked):")
    print("-" * 80)
    print(text)

    result = add_clickable_issue_links(text, issue_map)

    print("\nAFTER (should be unchanged):")
    print("-" * 80)
    print(result)

    # Verify it wasn't double-processed
    assert result == text
    assert "[[**" not in result  # No double brackets

    print("\n✅ SUCCESS: Already linked issue IDs were not modified!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CLICKABLE ISSUE LINKS FIX - MANUAL TEST")
    print("=" * 80)
    print("\nThis script demonstrates the fix for clickable issue links.")
    print("The problem: Claude returns plain text 'LDRS-63' instead of bold '**LDRS-63**'")
    print("The solution: Two-pass approach that handles both plain and bold issue IDs")

    try:
        test_plain_text_scenario()
        test_already_bold_scenario()
        test_mixed_scenario()
        test_already_linked_scenario()

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✅")
        print("=" * 80)
        print("\nThe fix successfully:")
        print("1. Converts plain issue IDs (LDRS-63) to bold (**LDRS-63**)")
        print("2. Converts bold issue IDs to clickable links ([**LDRS-63**](url))")
        print("3. Handles emoji prefixes and colons correctly")
        print("4. Doesn't double-process already-linked issue IDs")
        print("5. Works for both conversation responses AND briefing responses")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise

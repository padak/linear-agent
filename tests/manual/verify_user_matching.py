#!/usr/bin/env python3
"""
Verification script for diacritic-aware user matching.

This script demonstrates how the user identity matching now works
correctly with Czech diacritics.
"""

from linear_chief.agent.context_builder import _normalize_name, _is_user_assignee


def test_normalization():
    """Test name normalization with various Czech names."""
    print("=" * 60)
    print("Testing Name Normalization")
    print("=" * 60)

    test_cases = [
        ("Petr Šimeček", "petr simecek"),
        ("Petr Simecek", "petr simecek"),
        ("PETR ŠIMEČEK", "petr simecek"),
        ("Tomáš Fejfar", "tomas fejfar"),
        ("Václav Nosek", "vaclav nosek"),
        ("Lukáš Řehořek", "lukas rehorek"),
    ]

    for input_name, expected in test_cases:
        result = _normalize_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{input_name}' → '{result}'")

    print()


def test_user_matching():
    """Test user assignee matching with diacritics."""
    print("=" * 60)
    print("Testing User Assignee Matching")
    print("=" * 60)

    # Simulate real-world scenario: LDRS-63
    print("\nScenario: LDRS-63 Bug Case")
    print("-" * 60)
    print("User config (.env):")
    print("  LINEAR_USER_NAME=Petr Simecek     (without diacritics)")
    print("  LINEAR_USER_EMAIL=petr@keboola.com")
    print()
    print("Linear assignee data:")
    print("  assignee_name=Petr Šimeček        (with diacritics: ě, č)")
    print("  assignee_email=petr@keboola.com")
    print()

    # Test the match
    is_match = _is_user_assignee(
        assignee_name="Petr Šimeček",
        assignee_email="petr@keboola.com",
        user_name="Petr Simecek",
        user_email="petr@keboola.com",
    )

    print(f"Match result: {'✓ MATCHED' if is_match else '✗ NO MATCH'}")
    print()

    if is_match:
        print("SUCCESS: Bot will now correctly identify LDRS-63 as user's issue!")
    else:
        print("ERROR: Bot still failing to match (this should not happen)")

    print()

    # Test other scenarios
    print("\nAdditional Test Cases:")
    print("-" * 60)

    test_cases = [
        (
            "Email match (different names)",
            "Tomáš Fejfar",
            "petr@keboola.com",
            "Petr Simecek",
            "petr@keboola.com",
            True,  # Email takes precedence
        ),
        (
            "Name match only (no email)",
            "Petr Šimeček",
            None,
            "Petr Simecek",
            "petr@keboola.com",
            True,
        ),
        (
            "Different user",
            "Tomáš Fejfar",
            "tomas@keboola.com",
            "Petr Simecek",
            "petr@keboola.com",
            False,
        ),
        (
            "Case insensitive",
            "PETR ŠIMEČEK",
            "PETR@KEBOOLA.COM",
            "petr simecek",
            "petr@keboola.com",
            True,
        ),
    ]

    for description, assignee_name, assignee_email, user_name, user_email, expected in test_cases:
        result = _is_user_assignee(
            assignee_name=assignee_name,
            assignee_email=assignee_email,
            user_name=user_name,
            user_email=user_email,
        )
        status = "✓" if result == expected else "✗"
        match_str = "MATCH" if result else "NO MATCH"
        print(f"{status} {description}: {match_str}")

    print()


def main():
    """Run all verification tests."""
    print()
    print("=" * 60)
    print("User Identity Matching Verification")
    print("=" * 60)
    print()

    test_normalization()
    test_user_matching()

    print("=" * 60)
    print("Verification Complete")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()

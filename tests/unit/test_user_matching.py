"""Tests for user identity matching with diacritic support.

Tests the _normalize_name and _is_user_assignee functions to ensure
robust matching across different name formats, diacritics, and case variations.
"""

from linear_chief.agent.context_builder import _normalize_name, _is_user_assignee


class TestNameNormalization:
    """Test diacritic removal and name normalization."""

    def test_czech_diacritics_simecek(self):
        """Test normalization of Šimeček (the actual bug case)."""
        assert _normalize_name("Petr Šimeček") == "petr simecek"
        assert _normalize_name("Petr Simecek") == "petr simecek"
        assert _normalize_name("PETR ŠIMEČEK") == "petr simecek"

    def test_czech_diacritics_various(self):
        """Test normalization of various Czech names."""
        assert _normalize_name("Tomáš Fejfar") == "tomas fejfar"
        assert _normalize_name("Václav Nosek") == "vaclav nosek"
        assert _normalize_name("Jakub Kotek") == "jakub kotek"
        assert _normalize_name("Lukáš Řehořek") == "lukas rehorek"
        assert _normalize_name("Ondřej Popelka") == "ondrej popelka"

    def test_all_czech_diacritics(self):
        """Test all Czech diacritic characters."""
        # Lowercase diacritics
        assert _normalize_name("á é í ó ú ý") == "a e i o u y"
        assert _normalize_name("č ď ě ň ř š ť ů ž") == "c d e n r s t u z"

        # Uppercase diacritics
        assert _normalize_name("Á É Í Ó Ú Ý") == "a e i o u y"
        assert _normalize_name("Č Ď Ě Ň Ř Š Ť Ů Ž") == "c d e n r s t u z"

    def test_case_insensitive(self):
        """Test case normalization."""
        assert _normalize_name("Petr Simecek") == "petr simecek"
        assert _normalize_name("PETR SIMECEK") == "petr simecek"
        assert _normalize_name("petr simecek") == "petr simecek"
        assert _normalize_name("PeTr SiMeCeK") == "petr simecek"

    def test_whitespace_handling(self):
        """Test whitespace normalization."""
        assert _normalize_name("  Petr Šimeček  ") == "petr simecek"
        assert (
            _normalize_name("Petr  Šimeček") == "petr  simecek"
        )  # Internal spaces preserved
        assert _normalize_name("\tPetr Šimeček\n") == "petr simecek"

    def test_empty_string(self):
        """Test empty string handling."""
        assert _normalize_name("") == ""
        assert _normalize_name("   ") == ""

    def test_single_word(self):
        """Test single-word names."""
        assert _normalize_name("Šimeček") == "simecek"
        assert _normalize_name("Tomáš") == "tomas"


class TestUserAssigneeMatching:
    """Test user assignee matching logic."""

    def test_email_match_exact(self):
        """Test exact email matching."""
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email="petr@keboola.com",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_email_match_case_insensitive(self):
        """Test case-insensitive email matching."""
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email="PETR@KEBOOLA.COM",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_email_match_with_whitespace(self):
        """Test email matching with whitespace."""
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email="  petr@keboola.com  ",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_name_match_with_diacritics(self):
        """Test name matching when assignee has diacritics."""
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email=None,
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_name_match_without_diacritics(self):
        """Test name matching when assignee doesn't have diacritics."""
        assert _is_user_assignee(
            assignee_name="Petr Simecek",
            assignee_email=None,
            user_name="Petr Šimeček",
            user_email="petr@keboola.com",
        )

    def test_name_match_case_insensitive(self):
        """Test case-insensitive name matching."""
        assert _is_user_assignee(
            assignee_name="PETR ŠIMEČEK",
            assignee_email=None,
            user_name="petr simecek",
            user_email="",
        )

    def test_name_match_various_users(self):
        """Test name matching for different users."""
        assert _is_user_assignee(
            assignee_name="Tomáš Fejfar",
            assignee_email=None,
            user_name="Tomas Fejfar",
            user_email="",
        )

        assert _is_user_assignee(
            assignee_name="Václav Nosek",
            assignee_email=None,
            user_name="Vaclav Nosek",
            user_email="",
        )

    def test_no_match_different_user(self):
        """Test that different users don't match."""
        assert not _is_user_assignee(
            assignee_name="Tomáš Fejfar",
            assignee_email="tomas@keboola.com",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_no_match_empty_fields(self):
        """Test that empty fields don't cause false matches."""
        assert not _is_user_assignee(
            assignee_name=None,
            assignee_email=None,
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_no_match_empty_user(self):
        """Test that empty user config doesn't match."""
        assert not _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email="petr@keboola.com",
            user_name="",
            user_email="",
        )

    def test_email_takes_precedence(self):
        """Test that email matching is checked first."""
        # This should match via email even though name is different
        assert _is_user_assignee(
            assignee_name="Tomáš Fejfar",
            assignee_email="petr@keboola.com",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_partial_data_email_only(self):
        """Test matching with only email data."""
        assert _is_user_assignee(
            assignee_name=None,
            assignee_email="petr@keboola.com",
            user_name="Petr Simecek",
            user_email="petr@keboola.com",
        )

    def test_partial_data_name_only(self):
        """Test matching with only name data."""
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",
            assignee_email=None,
            user_name="Petr Simecek",
            user_email="",
        )

    def test_real_world_scenario_ldrs63(self):
        """Test the actual LDRS-63 bug scenario."""
        # This is the exact case that was failing before
        assert _is_user_assignee(
            assignee_name="Petr Šimeček",  # From Linear
            assignee_email="petr@keboola.com",  # From Linear
            user_name="Petr Simecek",  # From .env (no diacritics)
            user_email="petr@keboola.com",  # From .env
        )


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_unicode_normalization_nfc_vs_nfd(self):
        """Test that both NFC and NFD forms are handled correctly."""
        # NFC: precomposed (é as single character)
        nfc_name = "José"

        # NFD: decomposed (e + combining accent)
        import unicodedata

        nfd_name = unicodedata.normalize("NFD", "José")

        # Both should normalize to the same result
        assert _normalize_name(nfc_name) == _normalize_name(nfd_name)
        assert _normalize_name(nfc_name) == "jose"

    def test_special_characters(self):
        """Test names with special characters."""
        assert _normalize_name("O'Connor") == "o'connor"
        assert _normalize_name("Jean-Pierre") == "jean-pierre"
        assert _normalize_name("Müller") == "muller"

    def test_numbers_in_name(self):
        """Test names with numbers (unusual but possible)."""
        assert _normalize_name("User123") == "user123"

    def test_very_long_name(self):
        """Test very long names."""
        long_name = "Petr " * 100 + "Šimeček"
        normalized = _normalize_name(long_name)
        assert "simecek" in normalized
        assert "š" not in normalized

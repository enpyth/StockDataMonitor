from app.auth import is_allowed_email


def test_is_allowed_email_allows_all_when_allowlist_is_empty():
    assert is_allowed_email("user@example.com", set()) is True


def test_is_allowed_email_matches_case_insensitively():
    assert is_allowed_email("Alice@Example.com", {"alice@example.com"}) is True


def test_is_allowed_email_rejects_unknown_email():
    assert is_allowed_email("mallory@example.com", {"alice@example.com"}) is False

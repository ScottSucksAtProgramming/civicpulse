from civicpulse.backend.privacy import redact


def test_redact_replaces_common_us_phone_numbers():
    assert redact("Call me at (631) 555-1212 tomorrow.") == "Call me at [REDACTED] tomorrow."
    assert redact("Backup number is 631-555-3434.") == "Backup number is [REDACTED]."


def test_redact_replaces_email_addresses():
    assert redact("Email jane.resident@example.com with updates.") == (
        "Email [REDACTED] with updates."
    )


def test_redact_replaces_street_addresses():
    assert redact("The issue is near 200 East Sunrise Highway.") == (
        "The issue is near [REDACTED]."
    )


def test_redact_replaces_ssns():
    assert redact("My SSN is 123-45-6789.") == "My SSN is [REDACTED]."


def test_redact_replaces_honorific_and_name():
    assert redact("Please contact Mr. Smith about the permit.") == (
        "Please contact [REDACTED] about the permit."
    )


def test_redact_leaves_non_pii_text_unchanged():
    text = "A resident is concerned about traffic near a school."
    assert redact(text) == text

import pytest
from app.services.html_validator import HTMLAllowlistValidator


def test_valid_conservative_html_description():
    valid_html = (
        "<h4>Proven Framework</h4>"
        "<p>This is a paragraph with <b>bold</b>, <i>italic</i>, <em>emphasis</em>, and <u>underline</u> text.<br>"
        "Next line after void break tag.</p>"
        "<ul>"
        "<li>First actionable takeaway</li>"
        "<li>Second actionable takeaway</li>"
        "</ul>"
    )
    violations = HTMLAllowlistValidator.validate_description(valid_html)
    assert len(violations) == 0


def test_void_br_tag_and_repeated_br():
    """Verify that <br>, <br/>, and repeated <br><br> parse cleanly without stack disruption."""
    html_with_br = "<p>Line one<br>Line two<br/><br>Line three</p>"
    violations = HTMLAllowlistValidator.validate_description(html_with_br)
    assert len(violations) == 0


def test_prohibited_tags_rejected():
    # <h1> is excluded from conservative policy
    v_h1 = HTMLAllowlistValidator.validate_description("<h1>Major Title</h1><p>Text</p>")
    assert any("h1" in v.message for v in v_h1)

    # <a> is prohibited
    v_a = HTMLAllowlistValidator.validate_description("<p>Visit our website <a href='https://example.com'>here</a></p>")
    assert any("a" in v.message for v in v_a)

    # <script> is prohibited
    v_script = HTMLAllowlistValidator.validate_description("<script>alert('xss')</script>")
    assert any("script" in v.message for v in v_script)


def test_html_attributes_strictly_rejected():
    html_with_attr = "<p style='color:red;'>Styled paragraph</p>"
    violations = HTMLAllowlistValidator.validate_description(html_with_attr)
    assert len(violations) > 0
    assert any("attributes are not permitted" in v.message for v in violations)


def test_unclosed_and_mismatched_tags():
    # Unclosed tag
    v_unclosed = HTMLAllowlistValidator.validate_description("<p>Unclosed paragraph")
    assert any("Unclosed" in v.message for v in v_unclosed)

    # Mismatched nesting
    v_mismatch = HTMLAllowlistValidator.validate_description("<p><b>Mismatched</b></i></p>")
    assert any("Mismatched" in v.message or "Unexpected" in v.message for v in v_mismatch)


def test_text_entities_safely_preserved():
    html_with_entities = "<p>Tom &amp; Jerry's Guide: Price &lt; $50 &amp; Quality &gt; 90%.</p>"
    violations = HTMLAllowlistValidator.validate_description(html_with_entities)
    assert len(violations) == 0


def test_max_length_exceeded():
    long_html = "<p>" + "A" * 4001 + "</p>"
    violations = HTMLAllowlistValidator.validate_description(long_html)
    assert any("exceeds maximum allowed 4,000 characters" in v.message for v in violations)

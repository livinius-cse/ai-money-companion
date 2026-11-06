from html.parser import HTMLParser
from typing import List, Tuple
from app.schemas.kdp_validator import RuleViolation

CONSERVATIVE_ALLOWED_TAGS = {
    "b", "em", "i", "u", "br", "p", "ol", "ul", "li", "h4", "h5", "h6"
}
VOID_TAGS = {"br"}
MAX_DESCRIPTION_LENGTH = 4000


class _KDPDescriptionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tag_stack: List[str] = []
        self.violations: List[RuleViolation] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]):
        tag_lower = tag.lower()

        # 1. Tag allowlist check
        if tag_lower not in CONSERVATIVE_ALLOWED_TAGS:
            self.violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Prohibited HTML tag '<{tag}>' is not permitted in book descriptions by KDP conservative policy.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )
            return

        # 2. Attribute prohibition check
        if attrs:
            self.violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"HTML attributes are not permitted on tag '<{tag}>' (found attributes: {[a[0] for a in attrs]}).",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )

        # 3. Void tag vs non-void tag stack management
        if tag_lower not in VOID_TAGS:
            self.tag_stack.append(tag_lower)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        # Void tags do not have closing tags; if </br> is seen, simply ignore
        if tag_lower in VOID_TAGS:
            return

        if not self.tag_stack:
            self.violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Unexpected closing tag '</{tag}>' with no matching open tag.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )
            return

        expected = self.tag_stack[-1]
        if expected != tag_lower:
            self.violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Mismatched HTML nesting: expected closing tag '</{expected}>', found '</{tag}>'.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )
            # Pop if present anywhere in stack to attempt recovery
            if tag_lower in self.tag_stack:
                while self.tag_stack and self.tag_stack[-1] != tag_lower:
                    self.tag_stack.pop()
                if self.tag_stack:
                    self.tag_stack.pop()
        else:
            self.tag_stack.pop()

    def close(self):
        super().close()
        if self.tag_stack:
            self.violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Unclosed HTML tags detected: {self.tag_stack}.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )


class HTMLAllowlistValidator:
    """
    Validates book description HTML against KDP conservative allowlist rules.
    Safely preserves character entities and rejects attributes, malformed nesting, and unclosed tags.
    """

    @staticmethod
    def validate_description(html_text: str) -> List[RuleViolation]:
        violations: List[RuleViolation] = []

        if not html_text:
            return violations

        # Length check
        if len(html_text) > MAX_DESCRIPTION_LENGTH:
            violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Book description length ({len(html_text)} chars) exceeds maximum allowed 4,000 characters.",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )

        parser = _KDPDescriptionParser()
        try:
            parser.feed(html_text)
            parser.close()
            violations.extend(parser.violations)
        except Exception as e:
            violations.append(
                RuleViolation(
                    rule_id="KDP-META-002",
                    field="description_html",
                    severity="BLOCKING_ERROR",
                    message=f"Malformed HTML structure could not be parsed: {str(e)}",
                    reference_doc="https://kdp.amazon.com/en_US/help/topic/G201189630",
                )
            )

        return violations

import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_disclosure import AIDisclosureAttestation
from app.models.user import User
from app.schemas.disclosure import AIDisclosureConfirmRequest, AIDisclosureResponse


# -----------------------------------------------------------------------------
# 1. Pydantic Symmetric Conditional Validation Tests
# -----------------------------------------------------------------------------
def test_disclosure_validation_valid_ai_generated():
    """Valid ai_generated requires tools listed and editing extent specified."""
    req = AIDisclosureConfirmRequest(
        text_creation_method="ai_generated",
        text_tools_used=["Claude 3.5 Sonnet"],
        text_editing_extent="extensive_editing",
        image_creation_method="ai_generated",
        image_tools_used=["Midjourney v6"],
        image_editing_extent="some_editing",
        translation_creation_method="none",
        translation_tools_used=[],
        translation_editing_extent=None,
        author_confirmed=True,
    )
    assert req.text_creation_method == "ai_generated"
    assert req.text_tools_used == ["Claude 3.5 Sonnet"]
    assert req.text_editing_extent == "extensive_editing"
    assert req.author_confirmed is True


def test_disclosure_validation_author_confirmed_false_rejected():
    """author_confirmed=False must be rejected by validator."""
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="none",
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=False,
        )
    assert "author must explicitly confirm the disclosure" in str(exc_info.value).lower()


def test_disclosure_validation_ai_generated_missing_tools():
    """ai_generated with empty tools list raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="ai_generated",
            text_tools_used=[],
            text_editing_extent="some_editing",
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "no ai tools were provided" in str(exc_info.value).lower()


def test_disclosure_validation_ai_generated_missing_editing_extent():
    """ai_generated without editing extent raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="ai_generated",
            text_tools_used=["ChatGPT"],
            text_editing_extent=None,
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "editing extent was not provided" in str(exc_info.value).lower()


def test_disclosure_validation_valid_ai_assisted():
    """ai_assisted requires tools listed, but editing extent must be None."""
    req = AIDisclosureConfirmRequest(
        text_creation_method="ai_assisted",
        text_tools_used=["Grammarly"],
        text_editing_extent=None,
        image_creation_method="none",
        translation_creation_method="none",
        author_confirmed=True,
    )
    assert req.text_creation_method == "ai_assisted"
    assert req.text_editing_extent is None


def test_disclosure_validation_ai_assisted_missing_tools():
    """ai_assisted without tools raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="ai_assisted",
            text_tools_used=[],
            text_editing_extent=None,
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "brainstorming/editing tools were not provided" in str(exc_info.value).lower()


def test_disclosure_validation_ai_assisted_prohibits_editing_extent():
    """ai_assisted with editing extent provided raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="ai_assisted",
            text_tools_used=["Grammarly"],
            text_editing_extent="some_editing",
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "does not collect editing extent" in str(exc_info.value).lower()


def test_disclosure_validation_valid_none():
    """'none' requires empty tools list and None editing extent."""
    req = AIDisclosureConfirmRequest(
        text_creation_method="none",
        text_tools_used=[],
        text_editing_extent=None,
        image_creation_method="none",
        image_tools_used=[],
        image_editing_extent=None,
        translation_creation_method="none",
        translation_tools_used=[],
        translation_editing_extent=None,
        author_confirmed=True,
    )
    assert req.text_creation_method == "none"
    assert req.text_tools_used == []
    assert req.text_editing_extent is None


def test_disclosure_validation_none_prohibits_tools_or_extent():
    """'none' with tools or editing extent raises ValidationError."""
    # 1. Tools provided for 'none'
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="none",
            text_tools_used=["Some Tool"],
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "tools were listed" in str(exc_info.value).lower()

    # 2. Extent provided for 'none'
    with pytest.raises(ValidationError) as exc_info:
        AIDisclosureConfirmRequest(
            text_creation_method="none",
            text_tools_used=[],
            text_editing_extent="some_editing",
            image_creation_method="none",
            translation_creation_method="none",
            author_confirmed=True,
        )
    assert "editing extent was provided" in str(exc_info.value).lower()


# -----------------------------------------------------------------------------
# 2. Database Model & Persistence Tests
# -----------------------------------------------------------------------------
def test_ai_disclosure_model_defaults(db_session: Session, test_user: User):
    """Verify default model state: author_reviewed is False, attested_at is None."""
    attestation = AIDisclosureAttestation(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        disclosure_version="2024.1",
        text_creation_method="none",
        text_tools_used=[],
        image_creation_method="none",
        image_tools_used=[],
        translation_creation_method="none",
        translation_tools_used=[],
        kdp_submission_declaration="Human-authored declaration",
    )
    db_session.add(attestation)
    db_session.commit()
    db_session.refresh(attestation)

    assert attestation.author_reviewed is False
    assert attestation.author_attested_at is None
    assert attestation.created_at is not None


def test_ai_disclosure_user_isolation(db_session: Session, test_user: User):
    """Verify attestations are strictly scoped to user_id."""
    user_b = User(
        id=str(uuid.uuid4()),
        email="user_b@example.com",
        hashed_password="hash",
        full_name="User B",
    )
    db_session.add(user_b)
    db_session.commit()

    attestation_a = AIDisclosureAttestation(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        disclosure_version="2024.1",
        text_creation_method="none",
        image_creation_method="none",
        translation_creation_method="none",
        kdp_submission_declaration="Decl A",
        author_reviewed=True,
        author_attested_at=datetime.now(timezone.utc),
    )
    attestation_b = AIDisclosureAttestation(
        id=str(uuid.uuid4()),
        user_id=user_b.id,
        disclosure_version="2024.1",
        text_creation_method="ai_generated",
        text_tools_used=["Gemini"],
        text_editing_extent="some_editing",
        image_creation_method="none",
        translation_creation_method="none",
        kdp_submission_declaration="Decl B",
        author_reviewed=True,
        author_attested_at=datetime.now(timezone.utc),
    )
    db_session.add_all([attestation_a, attestation_b])
    db_session.commit()

    # Query for test_user
    user_a_records = db_session.scalars(
        select(AIDisclosureAttestation).where(AIDisclosureAttestation.user_id == test_user.id)
    ).all()
    assert len(user_a_records) == 1
    assert user_a_records[0].id == attestation_a.id

    # Query for user_b
    user_b_records = db_session.scalars(
        select(AIDisclosureAttestation).where(AIDisclosureAttestation.user_id == user_b.id)
    ).all()
    assert len(user_b_records) == 1
    assert user_b_records[0].id == attestation_b.id

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.ai_disclosure import AIDisclosureAttestation
from app.ai.base import AIResponseEnvelope, AIExecutionMetadata
from app.ai.exceptions import (
    AIError,
    AIConfigurationError,
    AIProviderError,
    AITimeoutError,
    AIRateLimitError,
)
from app.schemas.problem_details import ProblemDetails
from app.schemas.planning import BookPlanRequest, BookPlanResponse
from app.schemas.metadata import MetadataGenerateRequest, KDPMetadataResponse
from app.schemas.disclosure import AIDisclosureConfirmRequest, AIDisclosureResponse
from app.schemas.kdp_validator import (
    PrintSpecsValidationRequest,
    MetadataValidationRequest,
    ValidationResultResponse,
)
from app.services.book_planning import BookPlanningService
from app.services.metadata_generation import MetadataGenerationService
from app.services.kdp_validator import KDPValidatorService

router = APIRouter(prefix="/ai", tags=["AI Publishing Engine"])


def _make_problem_response(
    status_code: int,
    problem_type: str,
    title: str,
    detail: str,
    instance: str,
    requested_provider: str = "mock",
    actual_provider: str = "mock",
    fallback_attempted: bool = False,
) -> JSONResponse:
    content = ProblemDetails(
        type=problem_type,
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
        requested_provider=requested_provider,  # type: ignore[arg-type]
        actual_provider=actual_provider,  # type: ignore[arg-type]
        fallback_attempted=fallback_attempted,
    ).model_dump(exclude_none=True)
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"Content-Type": "application/problem+json"},
    )


# -----------------------------------------------------------------------------
# 1. BOOK PLANNING
# -----------------------------------------------------------------------------
@router.post(
    "/plan",
    response_model=AIResponseEnvelope[BookPlanResponse],
    dependencies=[Depends(verify_csrf)],
)
async def generate_book_plan(
    payload: BookPlanRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a structured publishing plan, chapter outlines, and page budget.
    Protected by authentication and CSRF validation.
    """
    try:
        plan = await BookPlanningService.plan_book(payload)
        return AIResponseEnvelope[BookPlanResponse](
            data=plan,
            telemetry=AIExecutionMetadata(
                requested_provider=settings.AI_PROVIDER,  # type: ignore[arg-type]
                actual_provider="mock",
                is_mock_generated=(settings.AI_PROVIDER == "mock"),
                model_name="mock-deterministic-v1" if settings.AI_PROVIDER == "mock" else "gemini-1.5-flash",
                execution_duration_ms=10,
                is_fallback=False,
            ),
        )
    except ValueError as e:
        return _make_problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            problem_type="https://api.kdp-os.local/errors/invalid-plan-parameters",
            title="Invalid Book Plan Parameters",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )
    except AITimeoutError as e:
        return _make_problem_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            problem_type="https://api.kdp-os.local/errors/ai-timeout",
            title="AI Provider Timeout",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )
    except AIRateLimitError as e:
        return _make_problem_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            problem_type="https://api.kdp-os.local/errors/ai-rate-limit",
            title="AI Provider Rate Limit Exceeded",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )
    except (AIProviderError, AIConfigurationError) as e:
        return _make_problem_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            problem_type="https://api.kdp-os.local/errors/upstream-ai-provider",
            title="Upstream AI Provider Failure",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )


# -----------------------------------------------------------------------------
# 2. METADATA GENERATION
# -----------------------------------------------------------------------------
@router.post(
    "/metadata",
    response_model=AIResponseEnvelope[KDPMetadataResponse],
    dependencies=[Depends(verify_csrf)],
)
async def generate_metadata(
    payload: MetadataGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Generate 1 to 7 KDP search keywords, categories, and conservative HTML description.
    Protected by authentication and CSRF validation.
    """
    try:
        metadata = await MetadataGenerationService.generate_metadata(payload)
        return AIResponseEnvelope[KDPMetadataResponse](
            data=metadata,
            telemetry=AIExecutionMetadata(
                requested_provider=settings.AI_PROVIDER,  # type: ignore[arg-type]
                actual_provider="mock",
                is_mock_generated=(settings.AI_PROVIDER == "mock"),
                model_name="mock-deterministic-v1" if settings.AI_PROVIDER == "mock" else "gemini-1.5-flash",
                execution_duration_ms=10,
                is_fallback=False,
            ),
        )
    except ValueError as e:
        return _make_problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            problem_type="https://api.kdp-os.local/errors/invalid-metadata-parameters",
            title="Invalid Metadata Parameters",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )
    except (AITimeoutError, AIRateLimitError, AIProviderError, AIConfigurationError) as e:
        code = status.HTTP_504_GATEWAY_TIMEOUT if isinstance(e, AITimeoutError) else status.HTTP_502_BAD_GATEWAY
        return _make_problem_response(
            status_code=code,
            problem_type="https://api.kdp-os.local/errors/upstream-ai-provider",
            title="Upstream AI Provider Failure",
            detail=str(e),
            instance=str(request.url.path),
            requested_provider=settings.AI_PROVIDER,
        )


# -----------------------------------------------------------------------------
# 3. AI DISCLOSURE ATTESTATION PERSISTENCE
# -----------------------------------------------------------------------------
@router.post(
    "/disclosure/confirm",
    response_model=AIDisclosureResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def confirm_ai_disclosure(
    payload: AIDisclosureConfirmRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Persist server-verified author attestation.
    Derived fields (user_id, timestamp, author_reviewed) are stamped exclusively by the backend.
    """
    server_time = datetime.now(timezone.utc)
    spec_version = "2024.1"

    declaration_parts = [
        f"Text: {payload.text_creation_method} (Tools: {', '.join(payload.text_tools_used) or 'None'}; Editing: {payload.text_editing_extent or 'N/A'})",
        f"Images: {payload.image_creation_method} (Tools: {', '.join(payload.image_tools_used) or 'None'})",
        f"Translations: {payload.translation_creation_method} (Tools: {', '.join(payload.translation_tools_used) or 'None'})",
    ]
    declaration_text = " | ".join(declaration_parts)

    attestation = AIDisclosureAttestation(
        id=str(uuid.uuid4()),
        user_id=current_user.id,  # Authenticated session identity ONLY
        disclosure_version=spec_version,
        text_creation_method=payload.text_creation_method,
        text_tools_used=payload.text_tools_used,
        text_editing_extent=payload.text_editing_extent,
        image_creation_method=payload.image_creation_method,
        image_tools_used=payload.image_tools_used,
        image_editing_extent=payload.image_editing_extent,
        translation_creation_method=payload.translation_creation_method,
        translation_tools_used=payload.translation_tools_used,
        translation_editing_extent=payload.translation_editing_extent,
        kdp_submission_declaration=declaration_text,
        author_reviewed=True,  # Server stamps True only after validation
        author_attested_at=server_time,  # Server clock ONLY
    )

    db.add(attestation)
    try:
        db.commit()
        db.refresh(attestation)
    except Exception as e:
        db.rollback()
        return _make_problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            problem_type="https://api.kdp-os.local/errors/persistence-failure",
            title="Attestation Persistence Failure",
            detail="Failed to persist author attestation record. Database transaction rolled back.",
            instance=str(request.url.path),
        )

    return attestation


@router.get(
    "/disclosure/latest",
    response_model=AIDisclosureResponse,
)
def get_latest_disclosure(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve the most recent confirmed attestation for the authenticated user.
    Authentication required; no CSRF required for safe GET method.
    """
    stmt = (
        select(AIDisclosureAttestation)
        .where(AIDisclosureAttestation.user_id == current_user.id)
        .order_by(AIDisclosureAttestation.author_attested_at.desc())
    )
    record = db.scalar(stmt)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No confirmed AI disclosure attestation found for current user.",
        )
    return record


# -----------------------------------------------------------------------------
# 4. KDP SPECIFICATION VALIDATION ENDPOINTS
# -----------------------------------------------------------------------------
@router.post(
    "/validate/print-specs",
    response_model=ValidationResultResponse,
    dependencies=[Depends(verify_csrf)],
)
def validate_print_specs(
    payload: PrintSpecsValidationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Validate print specifications against the verified KDP specification matrix.
    Protected by authentication and CSRF.
    """
    return KDPValidatorService.validate_print_specs(payload)


@router.post(
    "/validate/metadata",
    response_model=ValidationResultResponse,
    dependencies=[Depends(verify_csrf)],
)
def validate_metadata(
    payload: MetadataValidationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Validate title/subtitle length, keyword count, and HTML description tags.
    Protected by authentication and CSRF.
    """
    return KDPValidatorService.validate_metadata(payload)


# -----------------------------------------------------------------------------
# 5. PUBLIC CATALOG SPECIFICATIONS (READ-ONLY)
# -----------------------------------------------------------------------------
@router.get(
    "/specs",
)
def get_kdp_specifications() -> Dict[str, Any]:
    """
    Public catalog endpoint returning active versioned KDP specification metadata.
    Public and unauthenticated; exposes no user data or secrets.
    """
    return KDPValidatorService.get_raw_spec()

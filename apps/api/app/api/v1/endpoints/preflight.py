from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.book import Book
from app.schemas.preflight import PreFlightQAReport
from app.schemas.approval import (
    ApprovalSignOffRequest,
    ApprovalSnapshotResponse,
    ApprovalVerificationResult,
    ApprovalHistoryResponse,
)
from app.services.preflight_qa import PreFlightQAService
from app.services.approval import ApprovalService
from app.api.v1.endpoints.books import get_user_book_or_404

router = APIRouter(prefix="/books/{book_id}/preflight", tags=["Pre-Flight QA & Cryptographic Approval Gate"])


@router.get("/report", response_model=PreFlightQAReport)
def get_preflight_qa_report(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run comprehensive Pre-Flight QA audit and return structured findings with 5-way cryptographic hashes.
    Owner-scoped and read-only.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    report = PreFlightQAService.run_qa(db, book)
    return report


@router.post("/run", response_model=PreFlightQAReport, dependencies=[Depends(verify_csrf)])
def run_preflight_qa_audit(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger fresh end-to-end Pre-Flight QA inspection across manuscript, PDF documents,
    and metadata. Authenticated and CSRF protected.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    report = PreFlightQAService.run_qa(db, book)
    return report


@router.get("/approval", response_model=ApprovalVerificationResult)
def get_current_approval_status(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get active approval snapshot and verify that current stored files and manuscript
    match the cryptographic hashes recorded at approval time.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    result = ApprovalService.verify_approval_integrity(db, book)
    return result


@router.get("/approval/history", response_model=ApprovalHistoryResponse)
def get_approval_history(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve audit history of all approval snapshots, including invalidation reasons and timestamps.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    history = ApprovalService.get_approval_history(db, book.id, current_user.id)
    items = [ApprovalSnapshotResponse.model_validate(h) for h in history]
    return ApprovalHistoryResponse(items=items, total=len(items))


@router.post(
    "/approve",
    response_model=ApprovalSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def approve_book_for_publication(
    book_id: str,
    payload: ApprovalSignOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Explicit authenticated owner sign-off.
    Calculates five-way cryptographic hashes, freezes immutable snapshot,
    and transitions book status to APPROVED.
    Fails closed if blocking QA checks fail or required verification is unavailable.
    No approval permitted on GET requests.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    snapshot = ApprovalService.create_approval_snapshot(
        db=db,
        book=book,
        approving_user=current_user,
        attestation=payload.attestation,
    )
    return ApprovalSnapshotResponse.model_validate(snapshot)

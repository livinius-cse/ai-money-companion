from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.schemas.illustration import (
    IllustrationCreate,
    IllustrationUpdate,
    IllustrationStatusUpdate,
    IllustrationResponse,
    IllustrationPromptGenerateRequest,
    IllustrationPromptGenerateResponse,
)
from app.core.storage import LocalAssetStorage, MAX_UPLOAD_SIZE_BYTES, detect_image_type
from app.services.illustration_prompt import IllustrationPromptService
from app.api.v1.endpoints.books import get_user_book_or_404

router = APIRouter(prefix="/books/{book_id}/illustrations", tags=["Illustrations & Asset Management"])


def get_user_illustration_or_404(
    db: Session, book_id: str, illustration_id: str, user_id: str
) -> Illustration:
    """Retrieve illustration ensuring strict book and user ownership isolation. Returns 404 for unauthorized access."""
    illustration = db.scalar(
        select(Illustration).where(
            Illustration.id == illustration_id,
            Illustration.book_id == book_id,
            Illustration.owner_id == user_id,
        )
    )
    if not illustration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Illustration not found.",
        )
    return illustration


@router.get("", response_model=List[IllustrationResponse])
def list_illustrations(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all illustrations and visual placeholders for a book."""
    get_user_book_or_404(db, book_id, current_user.id)
    illustrations = db.scalars(
        select(Illustration)
        .where(Illustration.book_id == book_id, Illustration.owner_id == current_user.id)
        .order_by(Illustration.created_at.desc())
    ).all()
    return illustrations


@router.post("", response_model=IllustrationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_illustration(
    book_id: str,
    payload: IllustrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new illustration prompt or reserved layout placeholder."""
    get_user_book_or_404(db, book_id, current_user.id)

    # If chapter_id is provided, verify it belongs to this book
    if payload.chapter_id:
        chap = db.scalar(
            select(Chapter).where(
                Chapter.id == payload.chapter_id,
                Chapter.book_id == book_id,
                Chapter.owner_id == current_user.id,
            )
        )
        if not chap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced chapter does not exist in this book.",
            )

    illustration = Illustration(
        book_id=book_id,
        chapter_id=payload.chapter_id,
        owner_id=current_user.id,
        prompt=payload.prompt,
        description=payload.description,
        style_preset=payload.style_preset,
        seed=payload.seed,
        position_description=payload.position_description,
        status=payload.status,
    )
    db.add(illustration)
    db.commit()
    db.refresh(illustration)
    return illustration


@router.post("/generate-prompts", response_model=IllustrationPromptGenerateResponse, dependencies=[Depends(verify_csrf)])
async def generate_illustration_prompts(
    book_id: str,
    payload: IllustrationPromptGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate cohesive illustration prompts using AI based on book and chapter context."""
    book = get_user_book_or_404(db, book_id, current_user.id)

    chap_title = None
    chap_summary = None
    if payload.chapter_id:
        chap = db.scalar(
            select(Chapter).where(
                Chapter.id == payload.chapter_id,
                Chapter.book_id == book_id,
                Chapter.owner_id == current_user.id,
            )
        )
        if chap:
            chap_title = chap.title
            chap_summary = chap.summary

    service = IllustrationPromptService()
    envelope = await service.generate_prompts(
        book_title=book.title,
        book_topic=book.topic,
        chapter_title=chap_title,
        chapter_summary=chap_summary,
        req=payload,
    )
    return envelope.data


@router.get("/{illustration_id}", response_model=IllustrationResponse)
def get_illustration(
    book_id: str,
    illustration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full details of an individual illustration record."""
    return get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)


@router.put("/{illustration_id}", response_model=IllustrationResponse, dependencies=[Depends(verify_csrf)])
def update_illustration(
    book_id: str,
    illustration_id: str,
    payload: IllustrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update prompt text, description, position, or style preset."""
    illustration = get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        if hasattr(illustration, field):
            setattr(illustration, field, val)

    db.commit()
    db.refresh(illustration)
    return illustration


@router.patch("/{illustration_id}/status", response_model=IllustrationResponse, dependencies=[Depends(verify_csrf)])
def update_illustration_status(
    book_id: str,
    illustration_id: str,
    payload: IllustrationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Transition illustration lifecycle status with strict state machine rules.
    Transitions to APPROVED_FINAL require an image asset and explicit human approval.
    """
    illustration = get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)

    has_asset = bool(illustration.storage_key)
    is_valid, err_msg = IllustrationPromptService.validate_status_transition(
        current_status=illustration.status,
        new_status=payload.status,
        has_asset=has_asset,
        human_approved=payload.human_approved,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    illustration.status = payload.status
    db.commit()
    db.refresh(illustration)
    return illustration


@router.post("/{illustration_id}/upload", response_model=IllustrationResponse, dependencies=[Depends(verify_csrf)])
async def upload_illustration_asset(
    book_id: str,
    illustration_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Securely upload an image asset for an illustration placeholder.
    Validates magic byte signatures, computes SHA-256, and stores in private local storage.
    Automatically transitions status to GENERATED with asset_source='MANUAL_UPLOAD'.
    """
    illustration = get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 10MB upload limit.",
        )

    detected = detect_image_type(contents)
    if not detected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Only authentic PNG, JPEG, and WebP files are accepted.",
        )

    mime_type, _ = detected

    # Delete existing asset file if replacing
    if illustration.storage_key:
        LocalAssetStorage.delete_asset(illustration.storage_key)

    storage_key, size_bytes, sha256 = LocalAssetStorage.save_illustration_asset(
        book_id=book_id,
        illustration_id=illustration_id,
        file_bytes=contents,
        mime_type=mime_type,
    )

    illustration.storage_key = storage_key
    illustration.file_size_bytes = size_bytes
    illustration.sha256_hash = sha256
    illustration.mime_type = mime_type
    illustration.asset_source = "MANUAL_UPLOAD"
    illustration.status = "GENERATED"

    db.commit()
    db.refresh(illustration)
    return illustration


@router.get("/{illustration_id}/asset")
def get_illustration_asset(
    book_id: str,
    illustration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream private image asset with strict ownership authorization and cache controls."""
    illustration = get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)

    if not illustration.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No image asset attached to this illustration.",
        )

    asset_path = LocalAssetStorage.get_asset_path(illustration.storage_key)
    return FileResponse(
        path=str(asset_path),
        media_type=illustration.mime_type or "image/png",
        headers={
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "Content-Disposition": f'inline; filename="{illustration_id}.png"',
        },
    )


@router.delete("/{illustration_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
def delete_illustration(
    book_id: str,
    illustration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an illustration record and safely delete its file asset from private storage."""
    illustration = get_user_illustration_or_404(db, book_id, illustration_id, current_user.id)

    if illustration.storage_key:
        LocalAssetStorage.delete_asset(illustration.storage_key)

    db.delete(illustration)
    db.commit()
    return None

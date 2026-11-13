import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.schemas.chapter import (
    ChapterCreate,
    ChapterUpdate,
    ChapterResponse,
    ChapterReorderRequest,
)
from app.schemas.manuscript import (
    ManuscriptDraftRequest,
    ManuscriptDraftResponse,
    SectionExpandRequest,
    SectionExpandResponse,
    SectionRegenerateRequest,
    SectionRegenerateResponse,
)
from app.services.manuscript_generation import ManuscriptGenerationService
from app.api.v1.endpoints.books import get_user_book_or_404

router = APIRouter(prefix="/books/{book_id}/chapters", tags=["Chapters & Content Studio"])


def calculate_word_count(text: str) -> int:
    """Consistently count words separated by word boundaries, ignoring markdown punctuation."""
    return len(re.findall(r"\b\w+\b", text)) if text else 0


def estimate_reading_time(word_count: int) -> int:
    """Estimated reading time based on 200 WPM average reading speed."""
    return max(1, round(word_count / 200)) if word_count > 0 else 0


def _build_chapter_response(chapter: Chapter) -> ChapterResponse:
    wc = calculate_word_count(chapter.content)
    rt = estimate_reading_time(wc)
    return ChapterResponse(
        id=chapter.id,
        book_id=chapter.book_id,
        owner_id=chapter.owner_id,
        chapter_number=chapter.chapter_number,
        chapter_type=chapter.chapter_type,
        title=chapter.title,
        summary=chapter.summary,
        content=chapter.content,
        allocated_pages=chapter.allocated_pages,
        word_count=wc,
        estimated_reading_minutes=rt,
        draft_status=chapter.draft_status,
        created_at=chapter.created_at,
        updated_at=chapter.updated_at,
    )


def get_user_chapter_or_404(db: Session, book_id: str, chapter_id: str, user_id: str) -> Chapter:
    """Retrieve chapter ensuring strict book and user ownership isolation. Returns 404 for unauthorized access."""
    chapter = db.scalar(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.book_id == book_id,
            Chapter.owner_id == user_id,
        )
    )
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chapter not found.",
        )
    return chapter


@router.get("", response_model=List[ChapterResponse])
def list_chapters(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chapters for a given book ordered sequentially."""
    get_user_book_or_404(db, book_id, current_user.id)
    chapters = db.scalars(
        select(Chapter)
        .where(Chapter.book_id == book_id, Chapter.owner_id == current_user.id)
        .order_by(Chapter.chapter_number.asc())
    ).all()

    return [_build_chapter_response(c) for c in chapters]


@router.post("", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_chapter(
    book_id: str,
    payload: ChapterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new chapter within the book."""
    get_user_book_or_404(db, book_id, current_user.id)

    wc = calculate_word_count(payload.content or "")
    chapter = Chapter(
        book_id=book_id,
        owner_id=current_user.id,
        chapter_number=payload.chapter_number,
        chapter_type=payload.chapter_type,
        title=payload.title,
        summary=payload.summary,
        content=payload.content or "",
        allocated_pages=payload.allocated_pages,
        word_count=wc,
        draft_status=payload.draft_status,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    return _build_chapter_response(chapter)


@router.get("/{chapter_id}", response_model=ChapterResponse)
def get_chapter(
    book_id: str,
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full chapter details and Markdown content."""
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)
    return _build_chapter_response(chapter)


@router.put("/{chapter_id}", response_model=ChapterResponse, dependencies=[Depends(verify_csrf)])
def update_chapter(
    book_id: str,
    chapter_id: str,
    payload: ChapterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save chapter edits, update Markdown content, and recalculate word count."""
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)

    update_data = payload.model_dump(exclude_unset=True)
    if "content" in update_data and update_data["content"] is not None:
        chapter.content = update_data["content"]
        chapter.word_count = calculate_word_count(chapter.content)

    for field, val in update_data.items():
        if field != "content" and hasattr(chapter, field):
            setattr(chapter, field, val)

    db.commit()
    db.refresh(chapter)
    return _build_chapter_response(chapter)


@router.delete("/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
def delete_chapter(
    book_id: str,
    chapter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chapter from the book."""
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)
    db.delete(chapter)
    db.commit()
    return None


@router.post("/reorder", response_model=List[ChapterResponse], dependencies=[Depends(verify_csrf)])
def reorder_chapters(
    book_id: str,
    payload: ChapterReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atomically reorder chapters by updating their sequential numbering."""
    get_user_book_or_404(db, book_id, current_user.id)

    order_map = {item.chapter_id: item.chapter_number for item in payload.reordered_chapters}
    chapters = db.scalars(
        select(Chapter).where(Chapter.book_id == book_id, Chapter.owner_id == current_user.id)
    ).all()

    for chap in chapters:
        if chap.id in order_map:
            chap.chapter_number = order_map[chap.id]

    db.commit()

    updated_chapters = db.scalars(
        select(Chapter)
        .where(Chapter.book_id == book_id, Chapter.owner_id == current_user.id)
        .order_by(Chapter.chapter_number.asc())
    ).all()

    return [_build_chapter_response(c) for c in updated_chapters]


@router.post("/{chapter_id}/draft", response_model=ManuscriptDraftResponse, dependencies=[Depends(verify_csrf)])
async def draft_chapter_content(
    book_id: str,
    chapter_id: str,
    payload: ManuscriptDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate an AI manuscript draft for the chapter.
    Does NOT overwrite the database content automatically: returns draft for user review.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)

    service = ManuscriptGenerationService()
    envelope = await service.draft_chapter(
        book_title=book.title,
        book_topic=book.topic,
        target_audience=book.target_audience,
        chapter_number=chapter.chapter_number,
        chapter_title=chapter.title,
        chapter_summary=chapter.summary,
        req=payload,
    )
    return envelope.data


@router.post("/{chapter_id}/expand-section", response_model=SectionExpandResponse, dependencies=[Depends(verify_csrf)])
async def expand_chapter_section(
    book_id: str,
    chapter_id: str,
    payload: SectionExpandRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Expand a specific section of the manuscript with practical depth."""
    book = get_user_book_or_404(db, book_id, current_user.id)
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)

    service = ManuscriptGenerationService()
    envelope = await service.expand_section(
        book_topic=book.topic,
        chapter_title=chapter.title,
        req=payload,
    )
    return envelope.data


@router.post("/{chapter_id}/regenerate-section", response_model=SectionRegenerateResponse, dependencies=[Depends(verify_csrf)])
async def regenerate_chapter_section(
    book_id: str,
    chapter_id: str,
    payload: SectionRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a specific section with alternative instructions."""
    book = get_user_book_or_404(db, book_id, current_user.id)
    chapter = get_user_chapter_or_404(db, book_id, chapter_id, current_user.id)

    service = ManuscriptGenerationService()
    envelope = await service.regenerate_section(
        book_topic=book.topic,
        chapter_title=chapter.title,
        req=payload,
    )
    return envelope.data

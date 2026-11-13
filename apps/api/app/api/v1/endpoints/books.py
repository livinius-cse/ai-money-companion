from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete

from app.api.v1.deps import get_current_user, verify_csrf
from app.db.session import get_db
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.illustration import Illustration
from app.schemas.book import BookCreate, BookUpdate, BookResponse, BookListResponse
from app.schemas.planning import BookPlanRequest, BookPlanResponse, ApplyPlanRequest
from app.services.book_planning import BookPlanningService
from app.services.kdp_validator import KDPValidatorService
from app.schemas.kdp_validator import PrintSpecsValidationRequest

router = APIRouter(prefix="/books", tags=["Books & Product Studio"])


def get_user_book_or_404(db: Session, book_id: str, user_id: str) -> Book:
    """Retrieve book ensuring strict user ownership isolation. Returns 404 for unauthorized access."""
    book = db.scalar(select(Book).where(Book.id == book_id, Book.owner_id == user_id))
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found.",
        )
    return book


def _build_book_response(db: Session, book: Book) -> BookResponse:
    """Helper to populate computed aggregates on BookResponse."""
    chap_stats = db.execute(
        select(
            func.count(Chapter.id),
            func.coalesce(func.sum(Chapter.allocated_pages), 0),
            func.coalesce(func.sum(Chapter.word_count), 0),
        ).where(Chapter.book_id == book.id)
    ).first()

    ill_count = db.scalar(
        select(func.count(Illustration.id)).where(Illustration.book_id == book.id)
    ) or 0

    c_count = chap_stats[0] if chap_stats else 0
    alloc_pages = chap_stats[1] if chap_stats else 0
    words = chap_stats[2] if chap_stats else 0

    return BookResponse(
        id=book.id,
        owner_id=book.owner_id,
        title=book.title,
        subtitle=book.subtitle,
        topic=book.topic,
        book_concept=book.book_concept,
        target_audience=book.target_audience,
        target_reader_profile=book.target_reader_profile,
        book_type=book.book_type,
        print_format=book.print_format,
        marketplace=book.marketplace,
        trim_size=book.trim_size,
        paper_type=book.paper_type,
        target_page_count=book.target_page_count,
        status=book.status,
        front_matter_pages=book.front_matter_pages,
        back_matter_pages=book.back_matter_pages,
        created_at=book.created_at,
        updated_at=book.updated_at,
        chapter_count=c_count,
        total_allocated_pages=alloc_pages,
        total_word_count=words,
        illustration_count=ill_count,
    )


@router.get("", response_model=BookListResponse)
def list_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all books owned by the authenticated user."""
    books = db.scalars(
        select(Book).where(Book.owner_id == current_user.id).order_by(Book.updated_at.desc())
    ).all()

    items = [_build_book_response(db, b) for b in books]
    return BookListResponse(items=items, total=len(items))


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_csrf)])
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new book concept in Product Studio."""
    book = Book(
        owner_id=current_user.id,
        title=payload.title,
        subtitle=payload.subtitle,
        topic=payload.topic,
        book_concept=payload.book_concept,
        target_audience=payload.target_audience,
        target_reader_profile=payload.target_reader_profile,
        book_type=payload.book_type,
        print_format=payload.print_format,
        marketplace=payload.marketplace,
        trim_size=payload.trim_size,
        paper_type=payload.paper_type,
        target_page_count=payload.target_page_count,
        status="DRAFT",
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    return _build_book_response(db, book)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed book information by ID."""
    book = get_user_book_or_404(db, book_id, current_user.id)
    return _build_book_response(db, book)


@router.put("/{book_id}", response_model=BookResponse, dependencies=[Depends(verify_csrf)])
def update_book(
    book_id: str,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update book concept, positioning, or KDP manufacturing parameters."""
    book = get_user_book_or_404(db, book_id, current_user.id)

    update_dict = payload.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        if hasattr(book, field):
            setattr(book, field, val)

    db.commit()
    db.refresh(book)
    return _build_book_response(db, book)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_csrf)])
def delete_book(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a book draft and its cascaded chapters/illustrations."""
    book = get_user_book_or_404(db, book_id, current_user.id)
    db.delete(book)
    db.commit()
    return None


@router.post("/{book_id}/plan/generate", response_model=BookPlanResponse, dependencies=[Depends(verify_csrf)])
async def generate_plan_for_book(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a structured chapter and page plan based on the book's current concept."""
    book = get_user_book_or_404(db, book_id, current_user.id)

    req = BookPlanRequest(
        topic=book.topic,
        target_audience=book.target_audience or "General Readers",
        book_type="NON_FICTION",
        print_format=book.print_format,  # type: ignore[arg-type]
        marketplace=book.marketplace,
        target_trim_size=book.trim_size,
        paper_type=book.paper_type,
        target_pages=book.target_page_count,
    )
    plan = await BookPlanningService.plan_book(req)
    return plan


@router.post("/{book_id}/plan/apply", response_model=BookResponse, dependencies=[Depends(verify_csrf)])
def apply_plan_to_book(
    book_id: str,
    payload: ApplyPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Persist an accepted book plan: updates book title/metadata, front/back matter pages,
    and replaces or updates the chapters table in an atomic transaction.
    """
    book = get_user_book_or_404(db, book_id, current_user.id)

    # 1. Update book details
    book.title = payload.selected_title
    if payload.selected_subtitle:
        book.subtitle = payload.selected_subtitle
    if payload.target_reader_avatar:
        book.target_reader_profile = payload.target_reader_avatar
    book.front_matter_pages = payload.front_matter_pages
    book.back_matter_pages = payload.back_matter_pages
    book.status = "PLANNING"

    # 2. Clear existing chapters and insert new structured plan chapters
    db.execute(delete(Chapter).where(Chapter.book_id == book.id))

    for item in payload.chapters:
        chapter = Chapter(
            book_id=book.id,
            owner_id=current_user.id,
            chapter_number=item.chapter_number,
            chapter_type="chapter",
            title=item.title,
            summary=item.summary,
            content="",
            allocated_pages=item.allocated_pages,
            word_count=0,
            draft_status="NOT_STARTED",
        )
        db.add(chapter)

    db.commit()
    db.refresh(book)
    return _build_book_response(db, book)

import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.book import Book
from app.models.chapter import Chapter
from app.api.v1.endpoints.chapters import calculate_word_count, estimate_reading_time
from app.schemas.chapter import ChapterCreate, ChapterUpdate


def test_chapter_model_defaults(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Parent Book",
        topic="Personal Finance",
    )
    db_session.add(book)
    db_session.flush()

    chapter = Chapter(
        book_id=book.id,
        owner_id=test_user.id,
        chapter_number=1,
        title="Chapter 1: The Foundation",
    )
    db_session.add(chapter)
    db_session.flush()

    assert chapter.id is not None
    assert chapter.chapter_type == "chapter"
    assert chapter.allocated_pages == 10
    assert chapter.word_count == 0
    assert chapter.draft_status == "NOT_STARTED"
    assert chapter.content == ""


def test_word_count_and_reading_time_calculation():
    # 0 words
    assert calculate_word_count("") == 0
    assert estimate_reading_time(0) == 0

    # 100 words -> ~1 min
    text_100 = " ".join(["word"] * 100)
    assert calculate_word_count(text_100) == 100
    assert estimate_reading_time(100) == 1

    # 450 words -> ~2 mins
    text_450 = " ".join(["word"] * 450)
    assert calculate_word_count(text_450) == 450
    assert estimate_reading_time(450) == 2

    # Multiline with formatting (words: Header, First, paragraph, with, bold, text, Bullet, 1, Bullet, 2 = 10 words)
    md_text = "# Header\n\nFirst paragraph with **bold** text.\n\n- Bullet 1\n- Bullet 2"
    assert calculate_word_count(md_text) == 10


def test_chapter_schema_validation():
    req = ChapterCreate(
        chapter_number=2,
        title="Automating Your Savings",
        summary="Detailed steps to set up automated pay-yourself-first splits.",
        allocated_pages=15,
    )
    assert req.chapter_number == 2
    assert req.allocated_pages == 15

    # Negative or 0 chapter number rejected
    with pytest.raises(Exception):
        ChapterCreate(chapter_number=0, title="Invalid")

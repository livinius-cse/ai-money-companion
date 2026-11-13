import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate


def test_book_model_defaults(db_session: Session, test_user: User):
    book = Book(
        owner_id=test_user.id,
        title="Automated Wealth Systems",
        topic="Personal Finance",
    )
    db_session.add(book)
    db_session.flush()

    assert book.id is not None
    assert book.owner_id == test_user.id
    assert book.title == "Automated Wealth Systems"
    assert book.book_type == "non_fiction"
    assert book.print_format == "paperback"
    assert book.marketplace == "amazon_com"
    assert book.trim_size == "6x9"
    assert book.paper_type == "white_bw"
    assert book.target_page_count == 100
    assert book.status == "DRAFT"
    assert book.front_matter_pages == 4
    assert book.back_matter_pages == 2


def test_book_schema_validation():
    # Valid book creation
    req = BookCreate(
        title="Smart Money Blueprint",
        topic="Budgeting & Debt Snowball",
        target_audience="Young Professionals",
        target_page_count=120,
    )
    assert req.title == "Smart Money Blueprint"
    assert req.book_type == "non_fiction"
    assert req.target_page_count == 120

    # Validation failure: empty title
    with pytest.raises(Exception):
        BookCreate(title="", topic="Finance")

    # Validation failure: target page count below 24
    with pytest.raises(Exception):
        BookCreate(title="Valid Title", topic="Finance", target_page_count=10)

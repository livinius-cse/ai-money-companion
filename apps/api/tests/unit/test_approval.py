from sqlalchemy import select

from app.models.approval import BookApprovalSnapshot
from app.models.book import Book
from app.models.user import User
from app.services.approval import ApprovalService


def _approved_book(db_session, test_user: User) -> Book:
    book = Book(
        owner_id=test_user.id,
        title="Approved book",
        topic="Personal finance",
        status="APPROVED",
    )
    db_session.add(book)
    db_session.flush()
    db_session.add(
        BookApprovalSnapshot(
            book_id=book.id,
            owner_id=test_user.id,
            approving_user_id=test_user.id,
            snapshot_version=1,
            status="ACTIVE",
            manuscript_hash="a" * 64,
            metadata_hash="b" * 64,
            interior_hash="c" * 64,
            cover_hash="d" * 64,
            composite_hash="e" * 64,
            hash_scheme_version="kdp-sha256-v2",
            approval_attestation="I reviewed and approve this edition.",
        )
    )
    db_session.commit()
    return book


def test_mutation_invalidation_remains_in_callers_transaction(db_session, test_user: User):
    book = _approved_book(db_session, test_user)

    invalidated = ApprovalService.invalidate_active_approval(
        db_session,
        book.id,
        "Test mutation",
        commit=False,
    )

    assert invalidated is not None
    assert invalidated.status == "INVALIDATED"
    db_session.rollback()

    persisted_snapshot = db_session.scalar(
        select(BookApprovalSnapshot).where(BookApprovalSnapshot.book_id == book.id)
    )
    persisted_book = db_session.scalar(select(Book).where(Book.id == book.id))
    assert persisted_snapshot.status == "ACTIVE"
    assert persisted_book.status == "APPROVED"

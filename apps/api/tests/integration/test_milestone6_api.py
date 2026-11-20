import json
import hashlib

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import generate_csrf_token, get_password_hash
from app.models.book import Book
from app.models.sales import SalesImportBatch, SalesRecord
from app.models.user import User
from app.core.storage import LocalAssetStorage
from sqlalchemy import select


def _auth_headers(client: TestClient, user: User) -> dict:
    login_csrf = generate_csrf_token(identity="anonymous")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "StrongPassword123!"},
        headers={"X-CSRF-Token": login_csrf, "Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    return {
        "X-CSRF-Token": response.cookies["csrf_token"],
        "Origin": "http://localhost:3000",
    }


def _create_book(db_session: Session, owner: User) -> Book:
    book = Book(
        owner_id=owner.id,
        title="Private book",
        topic="Personal finance",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


def test_m6_sales_and_export_routes_require_authentication(
    client: TestClient,
    test_user: User,
    db_session: Session,
):
    book = _create_book(db_session, test_user)

    response = client.get(f"/api/v1/books/{book.id}/sales/analytics")

    assert response.status_code == 401


def test_m6_routes_enforce_book_owner_scope(
    client: TestClient,
    test_user: User,
    db_session: Session,
):
    other_user = User(
        email="m6_other@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="Other Publisher",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()
    db_session.refresh(other_user)
    book = _create_book(db_session, test_user)
    headers = _auth_headers(client, other_user)

    analytics = client.get(
        f"/api/v1/books/{book.id}/sales/analytics",
        headers=headers,
    )
    eligibility = client.get(
        f"/api/v1/books/{book.id}/exports/eligibility",
        headers=headers,
    )

    assert analytics.status_code == 404
    assert eligibility.status_code == 404


def test_m6_sales_import_requires_csrf(
    client: TestClient,
    test_user: User,
    db_session: Session,
):
    book = _create_book(db_session, test_user)
    _auth_headers(client, test_user)

    response = client.post(
        f"/api/v1/books/{book.id}/sales/import/confirm",
        files={"report": ("report.csv", b"invalid")},
        data={
            "report_type": "ORDERS",
            "column_mapping_json": "{}",
            "expected_source_sha256": hashlib.sha256(b"invalid").hexdigest(),
            "provenance": "REAL_KDP_REPORT",
        },
    )

    assert response.status_code == 403


def test_sales_import_requires_preview_mapping_and_confirmation(
    client: TestClient,
    test_user: User,
    db_session: Session,
    monkeypatch,
):
    book = _create_book(db_session, test_user)
    headers = _auth_headers(client, test_user)
    source_headers = [
        "Synthetic date",
        "Synthetic marketplace",
        "Synthetic title",
        "Synthetic paid units",
        "Synthetic free units",
    ]
    report_bytes = (
        ",".join(source_headers)
        + "\n2025-01-03,amazon.com,Private book,3,1\n"
    ).encode()
    mapping = {
        "reporting_period": source_headers[0],
        "marketplace": source_headers[1],
        "title": source_headers[2],
        "paid_units": source_headers[3],
        "free_units": source_headers[4],
    }

    def save_file(cls, owner_id, file_bytes, original_filename):
        return (
            f"{owner_id}/synthetic_report.csv",
            len(file_bytes),
            hashlib.sha256(file_bytes).hexdigest(),
            "synthetic_report.csv",
        )

    monkeypatch.setattr(
        LocalAssetStorage,
        "save_sales_import_file",
        classmethod(save_file),
    )

    initial_preview = client.post(
        f"/api/v1/books/{book.id}/sales/import/preview",
        files={"report": ("synthetic.csv", report_bytes)},
        data={"report_type": "ORDERS", "column_mapping_json": "{}"},
        headers=headers,
    )
    assert initial_preview.status_code == 200
    assert initial_preview.json()["source_headers"] == source_headers
    assert initial_preview.json()["can_import"] is False
    assert db_session.scalars(select(SalesImportBatch)).all() == []

    mapped_preview = client.post(
        f"/api/v1/books/{book.id}/sales/import/preview",
        files={"report": ("synthetic.csv", report_bytes)},
        data={
            "report_type": "ORDERS",
            "column_mapping_json": json.dumps(mapping),
        },
        headers=headers,
    )
    assert mapped_preview.status_code == 200
    preview_data = mapped_preview.json()
    assert preview_data["can_import"] is True
    assert preview_data["mapped_preview"][0]["paid_units"] == 3

    confirmed = client.post(
        f"/api/v1/books/{book.id}/sales/import/confirm",
        files={"report": ("synthetic.csv", report_bytes)},
        data={
            "report_type": "ORDERS",
            "column_mapping_json": json.dumps(mapping),
            "expected_source_sha256": preview_data["source_sha256"],
            "provenance": "REAL_KDP_REPORT",
        },
        headers=headers,
    )

    assert confirmed.status_code == 201
    assert confirmed.json()["status"] == "VALID"
    assert confirmed.json()["source_headers"] == source_headers
    records = db_session.scalars(select(SalesRecord)).all()
    assert len(records) == 1
    assert records[0].paid_units == 3
    assert records[0].free_units == 1

    changed_file = client.post(
        f"/api/v1/books/{book.id}/sales/import/confirm",
        files={"report": ("synthetic.csv", report_bytes + b"\n")},
        data={
            "report_type": "ORDERS",
            "column_mapping_json": json.dumps(mapping),
            "expected_source_sha256": preview_data["source_sha256"],
            "provenance": "REAL_KDP_REPORT",
        },
        headers=headers,
    )
    assert changed_file.status_code == 409
    assert len(db_session.scalars(select(SalesImportBatch)).all()) == 1

import csv
import hashlib
import io

import pytest
from openpyxl import Workbook
from sqlalchemy import select

from app.core.storage import LocalAssetStorage
from app.models.book import Book
from app.models.sales import SalesImportBatch, SalesRecord
from app.models.user import User
from app.schemas.sales import SalesReportType
from app.services.sales_analytics import DEMO_DISCLAIMER, SalesAnalyticsService
from app.services.sales_import import SalesImportService

ORDERS_HEADERS = [
    "Synthetic report date",
    "Synthetic marketplace",
    "Synthetic book title",
    "Synthetic paid units",
    "Synthetic free units",
]
ORDERS_MAPPING = {
    "reporting_period": "Synthetic report date",
    "marketplace": "Synthetic marketplace",
    "title": "Synthetic book title",
    "paid_units": "Synthetic paid units",
    "free_units": "Synthetic free units",
}
ROYALTY_HEADERS = [
    "Synthetic report period",
    "Synthetic marketplace",
    "Synthetic book title",
    "Synthetic royalty amount",
    "Synthetic currency",
]
ROYALTY_MAPPING = {
    "reporting_period": "Synthetic report period",
    "marketplace": "Synthetic marketplace",
    "title": "Synthetic book title",
    "royalty_amount": "Synthetic royalty amount",
    "currency": "Synthetic currency",
}


def _csv_bytes(headers, rows):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _book(db_session, test_user: User) -> Book:
    book = Book(
        owner_id=test_user.id,
        title="A Book",
        topic="Personal finance",
        print_format="paperback",
        trim_size="6x9",
        paper_type="white_bw",
    )
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


def _mock_storage(monkeypatch: pytest.MonkeyPatch):
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


def _preview(
    book: Book,
    filename: str,
    file_bytes: bytes,
    report_type: SalesReportType,
    mapping: dict[str, str],
    provenance: str = "REAL_KDP_REPORT",
):
    return SalesImportService.preview_report(
        filename=filename,
        file_bytes=file_bytes,
        book=book,
        report_type=report_type,
        column_mapping=mapping,
        provenance=provenance,
    )


def test_synthetic_orders_preview_requires_explicit_mapping(test_user: User):
    book = Book(owner_id=test_user.id, title="A Book", topic="Finance")
    report = _csv_bytes(
        ORDERS_HEADERS,
        [["2025-01-03", "amazon.com", "A Book", "12", "2"]],
    )

    unmapped = _preview(book, "synthetic.csv", report, "ORDERS", {})
    mapped = _preview(book, "synthetic.csv", report, "ORDERS", ORDERS_MAPPING)

    assert unmapped["source_headers"] == ORDERS_HEADERS
    assert not unmapped["can_import"]
    assert any("Map the required field" in error for error in unmapped["validation_errors"])
    assert mapped["can_import"]
    assert mapped["mapped_preview"][0]["paid_units"] == 12
    assert mapped["mapped_preview"][0]["free_units"] == 2
    assert mapped["mapped_preview"][0]["royalty_amount"] is None
    assert not mapped["mapped_preview"][0]["currency"]


def test_synthetic_xlsx_and_unknown_or_missing_mapping_validation(test_user: User):
    book = Book(owner_id=test_user.id, title="A Book", topic="Finance")
    headers_with_unmapped_field = ORDERS_HEADERS + ["Unrecognized synthetic metric"]
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers_with_unmapped_field)
    worksheet.append(["2025-01-03", "amazon.com", "A Book", 12, 2, "kept unmapped"])
    output = io.BytesIO()
    workbook.save(output)

    valid = _preview(book, "synthetic.xlsx", output.getvalue(), "ORDERS", ORDERS_MAPPING)
    unknown = _preview(
        book,
        "synthetic.xlsx",
        output.getvalue(),
        "ORDERS",
        {**ORDERS_MAPPING, "not_a_field": "Synthetic report date"},
    )
    missing = _preview(
        book,
        "synthetic.xlsx",
        output.getvalue(),
        "ORDERS",
        {key: value for key, value in ORDERS_MAPPING.items() if key != "free_units"},
    )
    invalid_header = _preview(
        book,
        "synthetic.xlsx",
        output.getvalue(),
        "ORDERS",
        {**ORDERS_MAPPING, "free_units": "Absent source header"},
    )

    assert valid["can_import"]
    assert valid["source_headers"] == headers_with_unmapped_field
    assert valid["source_preview"][0]["Unrecognized synthetic metric"] == "kept unmapped"
    assert not unknown["can_import"]
    assert any("unsupported canonical" in error for error in unknown["validation_errors"])
    assert not missing["can_import"]
    assert any("Map the required field" in error for error in missing["validation_errors"])
    assert not invalid_header["can_import"]
    assert any("does not match a detected header" in error for error in invalid_header["validation_errors"])


def test_invalid_values_are_reported_and_not_imported(
    db_session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    book = _book(db_session, test_user)
    file_bytes = _csv_bytes(
        ORDERS_HEADERS,
        [["not-a-date", "amazon.com", "A Book", "1.5", "-1"]],
    )
    _mock_storage(monkeypatch)

    preview = _preview(book, "synthetic.csv", file_bytes, "ORDERS", ORDERS_MAPPING)
    batch = SalesImportService.confirm_import(
        db_session,
        book,
        test_user,
        "synthetic.csv",
        file_bytes,
        "ORDERS",
        ORDERS_MAPPING,
        "REAL_KDP_REPORT",
        hashlib.sha256(file_bytes).hexdigest(),
    )

    assert not preview["can_import"]
    assert batch.status == "INVALID"
    assert batch.source_sha256 == hashlib.sha256(file_bytes).hexdigest()
    assert batch.source_headers == ORDERS_HEADERS
    assert batch.validation_result["errors"]
    assert db_session.scalars(select(SalesRecord)).all() == []


def test_import_confirmation_is_idempotent_for_same_source(
    db_session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    book = _book(db_session, test_user)
    file_bytes = _csv_bytes(
        ORDERS_HEADERS,
        [["2025-01-03", "amazon.com", "A Book", "12", "2"]],
    )
    _mock_storage(monkeypatch)

    first = SalesImportService.confirm_import(
        db_session,
        book,
        test_user,
        "synthetic.csv",
        file_bytes,
        "ORDERS",
        ORDERS_MAPPING,
        "REAL_KDP_REPORT",
        hashlib.sha256(file_bytes).hexdigest(),
    )
    second = SalesImportService.confirm_import(
        db_session,
        book,
        test_user,
        "synthetic.csv",
        file_bytes,
        "ORDERS",
        ORDERS_MAPPING,
        "REAL_KDP_REPORT",
        hashlib.sha256(file_bytes).hexdigest(),
    )

    assert first.id == second.id
    assert first.status == "VALID"
    assert first.column_mapping == ORDERS_MAPPING
    assert first.source_headers == ORDERS_HEADERS
    assert len(db_session.scalars(select(SalesImportBatch)).all()) == 1
    records = db_session.scalars(select(SalesRecord)).all()
    assert len(records) == 1
    assert records[0].paid_units == 12
    assert records[0].free_units == 2
    assert records[0].royalty_amount is None
    assert records[0].currency is None


def test_royalties_currency_and_real_demo_data_remain_separate(
    db_session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    book = _book(db_session, test_user)
    _mock_storage(monkeypatch)
    for provenance, currency, amount in (
        ("REAL_KDP_REPORT", "USD", "12.50"),
        ("REAL_KDP_REPORT", "GBP", "4.25"),
        ("SIMULATED_DEMO", "USD", "500.00"),
    ):
        file_bytes = _csv_bytes(
            ROYALTY_HEADERS,
            [["2025-01", "amazon.com", "A Book", amount, currency]],
        )
        SalesImportService.confirm_import(
            db_session,
            book,
            test_user,
            "synthetic_royalties.csv",
            file_bytes,
            "PRIOR_MONTH_ROYALTIES",
            ROYALTY_MAPPING,
            provenance,
            hashlib.sha256(file_bytes).hexdigest(),
        )

    real = SalesAnalyticsService.get_summary(
        db_session, book, test_user.id, "PRIOR_MONTH_ROYALTIES", "REAL_KDP_REPORT"
    )
    demo = SalesAnalyticsService.get_summary(
        db_session, book, test_user.id, "PRIOR_MONTH_ROYALTIES", "SIMULATED_DEMO"
    )
    orders_bytes = _csv_bytes(
        ORDERS_HEADERS,
        [["2025-01-03", "amazon.com", "A Book", "12", "2"]],
    )
    SalesImportService.confirm_import(
        db_session,
        book,
        test_user,
        "synthetic_orders.csv",
        orders_bytes,
        "ORDERS",
        ORDERS_MAPPING,
        "REAL_KDP_REPORT",
        hashlib.sha256(orders_bytes).hexdigest(),
    )
    orders = SalesAnalyticsService.get_summary(
        db_session, book, test_user.id, "ORDERS", "REAL_KDP_REPORT"
    )

    assert {item.currency: item.reported_royalties for item in real.royalty_totals} == {
        "GBP": 4.25,
        "USD": 12.5,
    }
    assert demo.is_demo
    assert demo.demo_disclaimer == DEMO_DISCLAIMER
    assert [item.reported_royalties for item in demo.royalty_totals] == [500.0]
    assert orders.total_paid_units == 12
    assert orders.total_free_units == 2
    assert orders.royalty_totals == []


def test_kenp_pages_are_stored_as_pages_not_order_units(
    db_session,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    book = _book(db_session, test_user)
    headers = [
        "Synthetic report date",
        "Synthetic marketplace",
        "Synthetic book title",
        "Synthetic KENP pages",
    ]
    mapping = {
        "reporting_period": headers[0],
        "marketplace": headers[1],
        "title": headers[2],
        "kenp_read_pages": headers[3],
    }
    file_bytes = _csv_bytes(headers, [["2025-01-03", "amazon.com", "A Book", "250"]])
    _mock_storage(monkeypatch)

    batch = SalesImportService.confirm_import(
        db_session,
        book,
        test_user,
        "synthetic_kenp.csv",
        file_bytes,
        "KENP_READ",
        mapping,
        "REAL_KDP_REPORT",
        hashlib.sha256(file_bytes).hexdigest(),
    )
    summary = SalesAnalyticsService.get_summary(
        db_session, book, test_user.id, "KENP_READ", "REAL_KDP_REPORT"
    )

    assert batch.status == "VALID"
    assert summary.total_kenp_read_pages == 250
    assert summary.total_paid_units == 0
    assert summary.total_free_units == 0
    assert summary.royalty_totals == []

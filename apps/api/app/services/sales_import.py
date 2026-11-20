import csv
import hashlib
import io
import math
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.storage import LocalAssetStorage
from app.models.book import Book
from app.models.sales import SalesImportBatch, SalesRecord
from app.models.user import User

SalesProvenance = Literal["REAL_KDP_REPORT", "SIMULATED_DEMO"]
SalesReportType = Literal["ORDERS", "KENP_READ", "PRIOR_MONTH_ROYALTIES"]
MAX_SALES_REPORT_SIZE_BYTES = 10 * 1024 * 1024
MAX_REPORT_ROWS = 50_000
MAX_REPORT_COLUMNS = 32
MAX_VALIDATION_ERRORS = 100

_REPORT_FIELDS = {
    "ORDERS": [
        {"key": "reporting_period", "label": "Reporting date or period", "required": True},
        {"key": "marketplace", "label": "Marketplace", "required": True},
        {"key": "title", "label": "Book title", "required": True},
        {"key": "asin", "label": "ASIN", "required": False},
        {"key": "format", "label": "Format", "required": False},
        {"key": "author", "label": "Author", "required": False},
        {"key": "paid_units", "label": "Paid units", "required": True},
        {"key": "free_units", "label": "Free units", "required": True},
    ],
    "KENP_READ": [
        {"key": "reporting_period", "label": "Reporting date or period", "required": True},
        {"key": "marketplace", "label": "Marketplace", "required": True},
        {"key": "title", "label": "Book title", "required": True},
        {"key": "asin", "label": "ASIN", "required": False},
        {"key": "author", "label": "Author", "required": False},
        {"key": "kenp_read_pages", "label": "KENP pages read", "required": True},
    ],
    "PRIOR_MONTH_ROYALTIES": [
        {"key": "reporting_period", "label": "Reporting date or period", "required": True},
        {"key": "marketplace", "label": "Marketplace", "required": True},
        {"key": "title", "label": "Book title", "required": True},
        {"key": "asin", "label": "ASIN", "required": False},
        {"key": "format", "label": "Format", "required": False},
        {"key": "author", "label": "Author", "required": False},
        {"key": "royalty_amount", "label": "Reported royalty amount", "required": True},
        {"key": "currency", "label": "Currency", "required": True},
    ],
}
SourceRow = Tuple[int, List[Any]]


class SalesImportValidationError(ValueError):
    """A user-uploaded report failed parsing or explicit mapping validation."""


def _header_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _source_value_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _read_rows(
    filename: str,
    file_bytes: bytes,
) -> Tuple[List[str], List[SourceRow], List[str]]:
    suffix = Path(filename).suffix.lower()
    errors: List[str] = []
    headers: List[str] = []
    rows: List[SourceRow] = []

    if suffix == ".csv":
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            return [], [], ["CSV reports must be UTF-8 encoded."]
        reader = csv.reader(io.StringIO(text, newline=""))
        try:
            raw_headers = next(reader, None)
        except csv.Error:
            return [], [], ["The CSV report contains malformed header data."]
        if not raw_headers:
            return [], [], ["The uploaded CSV has no header row."]
        headers = [_header_text(header) for header in raw_headers]
        if len(headers) > MAX_REPORT_COLUMNS:
            return headers, [], ["The report contains too many columns."]
        normalized = [unicodedata.normalize("NFC", header).strip().casefold() for header in headers]
        if any(not header for header in normalized):
            errors.append("The report contains a blank column header.")
        if len(set(normalized)) != len(normalized):
            errors.append("Duplicate column headers are ambiguous and cannot be mapped.")
        if errors:
            return headers, [], errors
        try:
            for row_number, values in enumerate(reader, start=2):
                if not any(value not in (None, "") for value in values):
                    continue
                if len(values) != len(headers):
                    errors.append(
                        f"Row {row_number}: The number of values does not match the detected headers."
                    )
                else:
                    rows.append((row_number, values))
                if len(rows) + len(errors) > MAX_REPORT_ROWS:
                    errors.append("The report exceeds the 50,000-row limit.")
                    break
        except csv.Error:
            errors.append("The CSV report contains malformed row data.")
        return headers, rows, errors[:MAX_VALIDATION_ERRORS]

    if suffix == ".xlsx":
        try:
            workbook = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=False)
        except (BadZipFile, InvalidFileException, OSError, ValueError):
            return [], [], ["The XLSX report is invalid or unreadable."]
        try:
            worksheet = workbook.active
            row_limit = worksheet.max_row or 0
            column_limit = worksheet.max_column or 0
            if row_limit > MAX_REPORT_ROWS + 1 or column_limit > MAX_REPORT_COLUMNS:
                return [], [], ["The report exceeds the supported row or column limit."]
            iterator = worksheet.iter_rows(values_only=True)
            raw_headers = next(iterator, None)
            if not raw_headers:
                return [], [], ["The uploaded XLSX has no header row."]
            headers = [_header_text(value) for value in raw_headers]
            normalized = [
                unicodedata.normalize("NFC", header).strip().casefold()
                for header in headers
            ]
            if any(not header for header in normalized):
                errors.append("The report contains a blank column header.")
            if len(set(normalized)) != len(normalized):
                errors.append("Duplicate column headers are ambiguous and cannot be mapped.")
            if errors:
                return headers, [], errors
            for row_number, values in enumerate(iterator, start=2):
                if not any(value not in (None, "") for value in values):
                    continue
                if len(values) > len(headers) and any(
                    value not in (None, "") for value in values[len(headers):]
                ):
                    errors.append(f"Row {row_number}: Values exist beyond the detected headers.")
                elif len(values) < len(headers):
                    rows.append((row_number, list(values) + [None] * (len(headers) - len(values))))
                else:
                    rows.append((row_number, list(values)))
                if len(rows) + len(errors) > MAX_REPORT_ROWS:
                    errors.append("The report exceeds the 50,000-row limit.")
                    break
            return headers, rows, errors[:MAX_VALIDATION_ERRORS]
        finally:
            workbook.close()

    return [], [], ["Only .csv and .xlsx report files are supported."]


def _parse_period(value: Any, row_number: int) -> Tuple[str, str]:
    if isinstance(value, datetime):
        parsed_date = value.date()
    elif isinstance(value, date):
        parsed_date = value
    else:
        text = str(value or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}", text):
            try:
                parsed_date = datetime.strptime(text, "%Y-%m").date().replace(day=1)
            except ValueError as exc:
                raise SalesImportValidationError(
                    f"Row {row_number}: Reporting date or period is invalid."
                ) from exc
        else:
            try:
                parsed_date = date.fromisoformat(text)
            except ValueError as exc:
                raise SalesImportValidationError(
                    f"Row {row_number}: Reporting date or period must be an ISO date or YYYY-MM."
                ) from exc
            if parsed_date.isoformat() != text:
                raise SalesImportValidationError(
                    f"Row {row_number}: Reporting date must use YYYY-MM-DD."
                )
    return parsed_date.strftime("%Y-%m"), parsed_date.isoformat()


def _parse_integer(value: Any, label: str, row_number: int) -> int:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise SalesImportValidationError(f"Row {row_number}: {label} must be a whole number.")
    if (
        not number.is_finite()
        or number != number.to_integral_value()
        or number < 0
        or number > Decimal("9223372036854775807")
    ):
        raise SalesImportValidationError(
            f"Row {row_number}: {label} must be a non-negative whole number."
        )
    return int(number)


def _parse_royalty(value: Any, row_number: int) -> float:
    try:
        amount = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise SalesImportValidationError(
            f"Row {row_number}: Reported royalty amount must be numeric."
        )
    if not amount.is_finite():
        raise SalesImportValidationError(
            f"Row {row_number}: Reported royalty amount must be finite."
        )
    try:
        result = float(amount)
    except OverflowError as exc:
        raise SalesImportValidationError(
            f"Row {row_number}: Reported royalty amount is outside the supported range."
        ) from exc
    if not math.isfinite(result):
        raise SalesImportValidationError(
            f"Row {row_number}: Reported royalty amount is outside the supported range."
        )
    return result


def _mapping_errors(
    report_type: SalesReportType,
    headers: List[str],
    column_mapping: Dict[str, str],
) -> List[str]:
    supported_fields = {field["key"] for field in _REPORT_FIELDS[report_type]}
    required_fields = {
        field["key"] for field in _REPORT_FIELDS[report_type] if field["required"]
    }
    errors: List[str] = []
    unknown_fields = set(column_mapping) - supported_fields
    if unknown_fields:
        errors.append("Mapping contains unsupported canonical fields.")
    for field in sorted(required_fields - set(column_mapping)):
        errors.append(
            f"Map the required field '{next(item['label'] for item in _REPORT_FIELDS[report_type] if item['key'] == field)}'."
        )
    for field, source_header in column_mapping.items():
        if source_header not in headers:
            errors.append(f"The mapping for '{field}' does not match a detected header.")
    mapped_headers = list(column_mapping.values())
    if len(set(mapped_headers)) != len(mapped_headers):
        errors.append("Each detected source column can be mapped to only one field.")
    return errors


def _source_preview(headers: List[str], rows: List[SourceRow]) -> List[Dict[str, Optional[str]]]:
    if len(set(headers)) != len(headers):
        return []
    return [
        {
            headers[index]: _source_value_text(value)
            for index, value in enumerate(values)
        }
        for _, values in rows[:5]
    ]


def _analyze_report(
    filename: str,
    file_bytes: bytes,
    book: Book,
    report_type: SalesReportType,
    column_mapping: Dict[str, str],
) -> Dict[str, Any]:
    source_hash = hashlib.sha256(file_bytes).hexdigest()
    headers, source_rows, errors = _read_rows(filename, file_bytes)
    mapping_errors = _mapping_errors(report_type, headers, column_mapping)
    errors.extend(mapping_errors)
    mapped_rows: List[Dict[str, Any]] = []
    periods: set[str] = set()
    marketplaces: set[str] = set()
    currencies: set[str] = set()
    seen: set[Tuple[Any, ...]] = set()

    if not errors:
        field_indexes = {
            field: headers.index(source_header)
            for field, source_header in column_mapping.items()
        }
        expected_title = " ".join(book.title.split()).casefold()
        for row_number, values in source_rows:
            try:
                period, transaction_date = _parse_period(
                    values[field_indexes["reporting_period"]],
                    row_number,
                )
                title = unicodedata.normalize(
                    "NFC",
                    str(values[field_indexes["title"]] or ""),
                ).strip()
                if (
                    not title
                    or " ".join(title.split()).casefold() != expected_title
                    or len(title) > 255
                ):
                    raise SalesImportValidationError(
                        f"Row {row_number}: Book title is empty, too long, or does not match the selected book."
                    )

                marketplace = unicodedata.normalize(
                    "NFC",
                    str(values[field_indexes["marketplace"]] or ""),
                ).strip()
                if not marketplace or len(marketplace) > 50:
                    raise SalesImportValidationError(
                        f"Row {row_number}: Marketplace is empty or exceeds the supported length."
                    )

                record: Dict[str, Any] = {
                    "report_type": report_type,
                    "transaction_date": transaction_date,
                    "reporting_period": period,
                    "title": title,
                    "marketplace": marketplace,
                    "asin_isbn": None,
                    "author": None,
                    "format": None,
                    "paid_units": 0,
                    "free_units": 0,
                    "kenp_read_pages": 0,
                    "units_sold": 0,
                    "units_refunded": 0,
                    "net_units": 0,
                    "currency": None,
                    "royalty_amount": None,
                    "source_row_number": row_number,
                }

                if "asin" in field_indexes:
                    asin = str(values[field_indexes["asin"]] or "").strip()
                    if len(asin) > 50:
                        raise SalesImportValidationError(
                            f"Row {row_number}: ASIN exceeds the supported length."
                        )
                    record["asin_isbn"] = asin or None
                if "author" in field_indexes:
                    author = str(values[field_indexes["author"]] or "").strip()
                    if len(author) > 255:
                        raise SalesImportValidationError(
                            f"Row {row_number}: Author exceeds the supported length."
                        )
                    record["author"] = author or None
                if "format" in field_indexes:
                    format_name = str(values[field_indexes["format"]] or "").strip()
                    if len(format_name) > 30:
                        raise SalesImportValidationError(
                            f"Row {row_number}: Format exceeds the supported length."
                        )
                    record["format"] = format_name or None

                if report_type == "ORDERS":
                    record["paid_units"] = _parse_integer(
                        values[field_indexes["paid_units"]], "Paid units", row_number
                    )
                    record["free_units"] = _parse_integer(
                        values[field_indexes["free_units"]], "Free units", row_number
                    )
                    record["units_sold"] = record["paid_units"] + record["free_units"]
                    record["net_units"] = record["units_sold"]
                elif report_type == "KENP_READ":
                    record["kenp_read_pages"] = _parse_integer(
                        values[field_indexes["kenp_read_pages"]],
                        "KENP pages read",
                        row_number,
                    )
                else:
                    currency = str(values[field_indexes["currency"]] or "").strip().upper()
                    if not re.fullmatch(r"[A-Z]{3}", currency):
                        raise SalesImportValidationError(
                            f"Row {row_number}: Currency must be a three-letter code."
                        )
                    record["currency"] = currency
                    record["royalty_amount"] = _parse_royalty(
                        values[field_indexes["royalty_amount"]], row_number
                    )
                    currencies.add(currency)

                identity = (
                    report_type,
                    record["transaction_date"],
                    record["marketplace"],
                    record["title"],
                    record["asin_isbn"],
                    record["format"],
                    record["paid_units"],
                    record["free_units"],
                    record["kenp_read_pages"],
                    record["currency"],
                    record["royalty_amount"],
                )
                if identity in seen:
                    raise SalesImportValidationError(f"Row {row_number}: Duplicate report row.")
                seen.add(identity)
                periods.add(period)
                marketplaces.add(marketplace)
                mapped_rows.append(record)
            except (SalesImportValidationError, KeyError) as exc:
                errors.append(str(exc) if isinstance(exc, SalesImportValidationError) else (
                    f"Row {row_number}: A mapped source column is missing."
                ))
                if len(errors) >= MAX_VALIDATION_ERRORS:
                    break

    if not source_rows and not errors:
        errors.append("The report contains no data rows.")

    source_preview = _source_preview(headers, source_rows)
    return {
        "source_sha256": source_hash,
        "report_type": report_type,
        "source_headers": headers,
        "column_mapping": column_mapping,
        "fields": _REPORT_FIELDS[report_type],
        "source_preview": source_preview,
        "mapped_preview": mapped_rows[:10] if not errors else mapped_rows[:10],
        "row_count": len(source_rows),
        "validation_errors": errors[:MAX_VALIDATION_ERRORS],
        "can_import": bool(source_rows) and not errors and len(mapped_rows) == len(source_rows),
        "records": mapped_rows,
        "reporting_period": next(iter(periods)) if len(periods) == 1 else None,
        "marketplace": next(iter(marketplaces)) if len(marketplaces) == 1 else None,
        "currency": next(iter(currencies)) if len(currencies) == 1 else None,
    }


class SalesImportService:
    @classmethod
    def preview_report(
        cls,
        filename: str,
        file_bytes: bytes,
        book: Book,
        report_type: SalesReportType,
        column_mapping: Dict[str, str],
        provenance: SalesProvenance,
    ) -> Dict[str, Any]:
        if len(file_bytes) > MAX_SALES_REPORT_SIZE_BYTES:
            raise SalesImportValidationError("The report exceeds the 10 MB upload limit.")
        if not file_bytes:
            raise SalesImportValidationError("The uploaded report is empty.")
        if report_type not in _REPORT_FIELDS:
            raise SalesImportValidationError("Unsupported KDP report type.")
        if provenance not in ("REAL_KDP_REPORT", "SIMULATED_DEMO"):
            raise SalesImportValidationError("Unsupported import provenance.")
        return _analyze_report(
            filename,
            file_bytes,
            book,
            report_type,
            column_mapping,
        )

    @classmethod
    def confirm_import(
        cls,
        db: Session,
        book: Book,
        owner: User,
        filename: str,
        file_bytes: bytes,
        report_type: SalesReportType,
        column_mapping: Dict[str, str],
        provenance: SalesProvenance,
        expected_source_sha256: str,
    ) -> SalesImportBatch:
        source_hash = hashlib.sha256(file_bytes).hexdigest()
        if source_hash != expected_source_sha256:
            raise SalesImportValidationError(
                "The uploaded file changed after preview; preview it again before confirming."
            )
        if len(file_bytes) > MAX_SALES_REPORT_SIZE_BYTES:
            raise SalesImportValidationError("The report exceeds the 10 MB upload limit.")
        if not file_bytes:
            raise SalesImportValidationError("The uploaded report is empty.")
        if report_type not in _REPORT_FIELDS:
            raise SalesImportValidationError("Unsupported KDP report type.")
        if provenance not in ("REAL_KDP_REPORT", "SIMULATED_DEMO"):
            raise SalesImportValidationError("Unsupported import provenance.")

        existing = db.scalar(
            select(SalesImportBatch).where(
                SalesImportBatch.owner_id == owner.id,
                SalesImportBatch.book_id == book.id,
                SalesImportBatch.source_sha256 == source_hash,
                SalesImportBatch.report_type == report_type,
                SalesImportBatch.provenance == provenance,
            )
        )
        if existing:
            return existing

        analysis = _analyze_report(
            filename,
            file_bytes,
            book,
            report_type,
            column_mapping,
        )
        storage_key, _, stored_hash, safe_filename = LocalAssetStorage.save_sales_import_file(
            owner_id=owner.id,
            file_bytes=file_bytes,
            original_filename=filename,
        )
        if stored_hash != source_hash:
            LocalAssetStorage.get_sales_import_path(storage_key).unlink()
            raise RuntimeError("Sales report storage checksum did not match the uploaded bytes.")

        validation_result = {
            "errors": analysis["validation_errors"],
            "validated_row_count": len(analysis["records"]) if analysis["can_import"] else 0,
        }
        batch = SalesImportBatch(
            owner_id=owner.id,
            book_id=book.id,
            original_filename=filename[:255],
            sanitized_filename=safe_filename[:255],
            storage_key=storage_key,
            report_type=report_type,
            source_headers=analysis["source_headers"],
            column_mapping=column_mapping,
            reporting_period=analysis["reporting_period"],
            marketplace=analysis["marketplace"],
            currency=analysis["currency"],
            source_sha256=source_hash,
            row_count=len(analysis["records"]) if analysis["can_import"] else 0,
            provenance=provenance,
            validation_result=validation_result,
            status="VALID" if analysis["can_import"] else "INVALID",
        )
        try:
            db.add(batch)
            db.flush()
            if analysis["can_import"]:
                for row in analysis["records"]:
                    db.add(
                        SalesRecord(
                            batch_id=batch.id,
                            owner_id=owner.id,
                            book_id=book.id,
                            report_type=report_type,
                            transaction_date=row["transaction_date"],
                            asin_isbn=row["asin_isbn"],
                            title=row["title"],
                            author=row["author"],
                            marketplace=row["marketplace"],
                            format=row["format"],
                            paid_units=row["paid_units"],
                            free_units=row["free_units"],
                            kenp_read_pages=row["kenp_read_pages"],
                            units_sold=row["units_sold"],
                            units_refunded=0,
                            net_units=row["net_units"],
                            currency=row["currency"],
                            royalty_amount=row["royalty_amount"],
                            raw_data={"source_row_number": row["source_row_number"]},
                            provenance=provenance,
                        )
                    )
            db.commit()
        except IntegrityError:
            db.rollback()
            LocalAssetStorage.get_sales_import_path(storage_key).unlink(missing_ok=True)
            existing = db.scalar(
                select(SalesImportBatch).where(
                    SalesImportBatch.owner_id == owner.id,
                    SalesImportBatch.book_id == book.id,
                    SalesImportBatch.source_sha256 == source_hash,
                    SalesImportBatch.report_type == report_type,
                    SalesImportBatch.provenance == provenance,
                )
            )
            if existing:
                return existing
            raise
        except Exception:
            db.rollback()
            LocalAssetStorage.get_sales_import_path(storage_key).unlink(missing_ok=True)
            raise

        db.refresh(batch)
        return batch

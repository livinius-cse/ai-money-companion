import hashlib
import json
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.exceptions import AIError
from app.api.v1.deps import get_current_user, verify_csrf
from app.api.v1.endpoints.books import get_user_book_or_404
from app.core.storage import LocalAssetStorage
from app.db.session import get_db
from app.models.approval import BookApprovalSnapshot
from app.models.export import KDPExportPackage
from app.models.sales import SalesImportBatch
from app.models.user import User
from app.schemas.export import (
    ExportEligibilityResponse,
    KDPExportPackageListResponse,
    KDPExportPackageResponse,
)
from app.schemas.recommendation import BusinessRecommendationResponse
from app.schemas.research import ResearchAssistanceRequest, ResearchAssistanceResponse
from app.schemas.sales import (
    SalesAnalyticsSummary,
    SalesImportBatchListResponse,
    SalesImportBatchResponse,
    SalesImportPreviewResponse,
    SalesProvenance,
    SalesReportType,
)
from app.services.approval import ApprovalService
from app.services.package_exporter import (
    KDPPackageExporterService,
    is_safe_zip_path,
)
from app.services.research_assistance import ResearchAssistanceService
from app.services.sales_analytics import SalesAnalyticsService
from app.services.sales_import import (
    MAX_SALES_REPORT_SIZE_BYTES,
    SalesImportService,
    SalesImportValidationError,
)

router = APIRouter(tags=["Milestone 6 - Export and Sales Intelligence"])
MAX_PACKAGE_MEMBER_BYTES = 650 * 1024 * 1024


@router.get(
    "/books/{book_id}/exports/eligibility",
    response_model=ExportEligibilityResponse,
)
def get_export_eligibility(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    return KDPPackageExporterService.check_eligibility(db, book)


@router.post(
    "/books/{book_id}/exports",
    response_model=KDPExportPackageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
def create_export(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    package = KDPPackageExporterService.export_kdp_package(db, book, current_user)
    return KDPExportPackageResponse.model_validate(package)


@router.get(
    "/books/{book_id}/exports",
    response_model=KDPExportPackageListResponse,
)
def list_exports(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    exports = KDPPackageExporterService.get_export_history(db, book.id, current_user.id)
    return KDPExportPackageListResponse(
        items=[KDPExportPackageResponse.model_validate(item) for item in exports],
        total=len(exports),
    )


@router.get(
    "/books/{book_id}/exports/{export_id}",
    response_model=KDPExportPackageResponse,
)
def get_export(
    book_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    package = db.scalar(
        select(KDPExportPackage).where(
            KDPExportPackage.id == export_id,
            KDPExportPackage.book_id == book.id,
            KDPExportPackage.owner_id == current_user.id,
        )
    )
    if not package:
        raise HTTPException(status_code=404, detail="Export package not found.")
    return KDPExportPackageResponse.model_validate(package)


def _verify_export_archive(path: Path, package: KDPExportPackage) -> None:
    if path.stat().st_size != package.file_size_bytes:
        raise HTTPException(status_code=409, detail="Stored export package size does not match its record.")

    digest = hashlib.sha256()
    with path.open("rb") as package_file:
        while True:
            chunk = package_file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    if digest.hexdigest() != package.sha256_hash:
        raise HTTPException(status_code=409, detail="Stored export package checksum does not match its record.")

    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [entry.filename for entry in infos]
            if len(names) != len(set(names)) or any(not is_safe_zip_path(name) for name in names):
                raise HTTPException(status_code=409, detail="Stored export archive contains unsafe member paths.")
            if "manifest.json" not in names:
                raise HTTPException(status_code=409, detail="Stored export archive has no manifest.")

            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if manifest != package.manifest_data:
                raise HTTPException(status_code=409, detail="Export manifest does not match its recorded manifest.")
            files = manifest.get("files")
            if not isinstance(files, dict) or set(names) != set(files) | {"manifest.json"}:
                raise HTTPException(status_code=409, detail="Export archive members do not match its manifest.")

            for name, metadata in files.items():
                if not isinstance(metadata, dict) or name not in names:
                    raise HTTPException(status_code=409, detail="Export manifest contains an invalid file entry.")
                info = archive.getinfo(name)
                if info.file_size > MAX_PACKAGE_MEMBER_BYTES:
                    raise HTTPException(status_code=409, detail="Export archive member exceeds the supported size.")
                member_hash = hashlib.sha256()
                member_size = 0
                with archive.open(info, "r") as member:
                    while True:
                        chunk = member.read(1024 * 1024)
                        if not chunk:
                            break
                        member_hash.update(chunk)
                        member_size += len(chunk)
                if (
                    member_size != metadata.get("size_bytes")
                    or member_hash.hexdigest() != metadata.get("sha256")
                ):
                    raise HTTPException(status_code=409, detail=f"Export member checksum mismatch: {name}.")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, zipfile.BadZipFile, KeyError) as exc:
        raise HTTPException(status_code=409, detail="Stored export archive is invalid or unreadable.") from exc


@router.get(
    "/books/{book_id}/exports/{export_id}/download",
    response_class=FileResponse,
)
def download_export(
    book_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    package = db.scalar(
        select(KDPExportPackage).where(
            KDPExportPackage.id == export_id,
            KDPExportPackage.book_id == book.id,
            KDPExportPackage.owner_id == current_user.id,
        )
    )
    if not package:
        raise HTTPException(status_code=404, detail="Export package not found.")

    verification = ApprovalService.verify_approval_integrity(db, book)
    if (
        not verification.is_valid
        or not verification.active_snapshot
        or verification.active_snapshot.id != package.approval_snapshot_id
    ):
        raise HTTPException(
            status_code=409,
            detail="The export's approval is no longer active. Run pre-flight QA and approve the current edition again.",
        )

    path = LocalAssetStorage.get_export_package_path(package.storage_key)
    _verify_export_archive(path, package)
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.zip", package.filename):
        raise HTTPException(status_code=409, detail="Export filename is invalid.")
    package.download_count += 1
    db.commit()
    return FileResponse(
        path,
        media_type="application/zip",
        filename=package.filename,
    )


def _parse_column_mapping(column_mapping_json: str) -> dict[str, str]:
    try:
        mapping = json.loads(column_mapping_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Column mapping must be valid JSON.") from exc
    if not isinstance(mapping, dict) or any(
        not isinstance(field, str) or not isinstance(header, str)
        for field, header in mapping.items()
    ):
        raise HTTPException(
            status_code=422,
            detail="Column mapping must map canonical field names to detected header strings.",
        )
    return mapping


@router.post(
    "/books/{book_id}/sales/import/preview",
    response_model=SalesImportPreviewResponse,
    dependencies=[Depends(verify_csrf)],
)
async def preview_sales_report(
    book_id: str,
    report: UploadFile = File(...),
    report_type: SalesReportType = Form(...),
    column_mapping_json: str = Form(default="{}"),
    provenance: SalesProvenance = Form(default="REAL_KDP_REPORT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    file_bytes = await report.read(MAX_SALES_REPORT_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_SALES_REPORT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Sales report exceeds the 10 MB upload limit.")
    try:
        analysis = SalesImportService.preview_report(
            filename=report.filename or "",
            file_bytes=file_bytes,
            book=book,
            report_type=report_type,
            column_mapping=_parse_column_mapping(column_mapping_json),
            provenance=provenance,
        )
    except SalesImportValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    analysis.pop("records", None)
    return SalesImportPreviewResponse.model_validate(
        {**analysis, "provenance": provenance}
    )


@router.post(
    "/books/{book_id}/sales/import/confirm",
    response_model=SalesImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def confirm_sales_report_import(
    book_id: str,
    report: UploadFile = File(...),
    report_type: SalesReportType = Form(...),
    column_mapping_json: str = Form(...),
    expected_source_sha256: str = Form(...),
    provenance: SalesProvenance = Form(default="REAL_KDP_REPORT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    file_bytes = await report.read(MAX_SALES_REPORT_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_SALES_REPORT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Sales report exceeds the 10 MB upload limit.")
    if not re.fullmatch(r"[a-f0-9]{64}", expected_source_sha256):
        raise HTTPException(status_code=422, detail="A valid preview SHA-256 is required.")
    if hashlib.sha256(file_bytes).hexdigest() != expected_source_sha256:
        raise HTTPException(
            status_code=409,
            detail="The uploaded file changed after preview; preview it again before confirming.",
        )
    try:
        batch = SalesImportService.confirm_import(
            db=db,
            book=book,
            owner=current_user,
            filename=report.filename or "",
            file_bytes=file_bytes,
            report_type=report_type,
            column_mapping=_parse_column_mapping(column_mapping_json),
            provenance=provenance,
            expected_source_sha256=expected_source_sha256,
        )
    except SalesImportValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SalesImportBatchResponse.model_validate(batch)


@router.get(
    "/books/{book_id}/sales/imports",
    response_model=SalesImportBatchListResponse,
)
def list_sales_imports(
    book_id: str,
    report_type: SalesReportType = Query(default="ORDERS"),
    provenance: SalesProvenance = Query(default="REAL_KDP_REPORT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    batches = list(
        db.scalars(
            select(SalesImportBatch)
            .where(
                SalesImportBatch.book_id == book.id,
                SalesImportBatch.owner_id == current_user.id,
                SalesImportBatch.report_type == report_type,
                SalesImportBatch.provenance == provenance,
            )
            .order_by(SalesImportBatch.created_at.desc())
        ).all()
    )
    return SalesImportBatchListResponse(
        items=[SalesImportBatchResponse.model_validate(batch) for batch in batches],
        total=len(batches),
    )


@router.get(
    "/books/{book_id}/sales/analytics",
    response_model=SalesAnalyticsSummary,
)
def get_sales_analytics(
    book_id: str,
    report_type: SalesReportType = Query(default="ORDERS"),
    provenance: SalesProvenance = Query(default="REAL_KDP_REPORT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    return SalesAnalyticsService.get_summary(
        db, book, current_user.id, report_type, provenance
    )


@router.post(
    "/books/{book_id}/research-assistance",
    response_model=ResearchAssistanceResponse,
    dependencies=[Depends(verify_csrf)],
)
async def research_assistance(
    book_id: str,
    payload: ResearchAssistanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    try:
        return await ResearchAssistanceService.assist(db, book, payload)
    except AIError as exc:
        raise HTTPException(
            status_code=503,
            detail="Configured AI provider is unavailable for research assistance.",
        ) from exc


@router.get(
    "/books/{book_id}/business-recommendations",
    response_model=BusinessRecommendationResponse,
)
def business_recommendations(
    book_id: str,
    report_type: SalesReportType = Query(default="ORDERS"),
    provenance: SalesProvenance = Query(default="REAL_KDP_REPORT"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = get_user_book_or_404(db, book_id, current_user.id)
    return SalesAnalyticsService.get_recommendations(
        db,
        book,
        current_user.id,
        report_type,
        provenance,
    )

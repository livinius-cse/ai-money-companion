from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ExportEligibilityResponse(BaseModel):
    is_eligible: bool
    active_approval_id: Optional[str] = None
    approval_version: Optional[int] = None
    hashes_verified: bool
    blocking_reasons: List[str] = Field(default_factory=list)
    interior_document_id: Optional[str] = None
    cover_document_id: Optional[str] = None
    current_composite_hash: Optional[str] = None
    approval_composite_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExportManifest(BaseModel):
    book_id: str
    book_title: str
    book_subtitle: Optional[str] = None
    print_format: str
    trim_size: str
    paper_type: str
    page_count: int
    marketplace: str
    export_version: int
    export_timestamp: str
    approval_snapshot_id: str
    approval_version: int
    approving_user_id: str
    hash_scheme_version: str
    component_hashes: Dict[str, str]
    files: Dict[str, Dict[str, Any]]
    hand_off_notice: str = "This package is prepared for manual publishing handoff to Amazon KDP (kdp.amazon.com). Automated upload is not performed."

    model_config = ConfigDict(from_attributes=True)


class KDPExportPackageResponse(BaseModel):
    id: str
    book_id: str
    owner_id: str
    approval_snapshot_id: Optional[str] = None
    export_version: int
    filename: str
    file_size_bytes: int
    sha256_hash: str
    manifest_data: Dict[str, Any]
    download_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KDPExportPackageListResponse(BaseModel):
    items: List[KDPExportPackageResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)

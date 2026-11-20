from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ApprovalSignOffRequest(BaseModel):
    attestation: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Explicit human approval attestation text confirming QA inspection and acceptance",
    )

    model_config = ConfigDict(from_attributes=True)


class ApprovalSnapshotResponse(BaseModel):
    id: str
    book_id: str
    owner_id: str
    approving_user_id: str
    snapshot_version: int
    status: str
    manuscript_hash: str
    metadata_hash: str
    interior_hash: str
    cover_hash: str
    composite_hash: str
    hash_scheme_version: str
    interior_document_id: Optional[str] = None
    interior_document_version: Optional[int] = None
    cover_document_id: Optional[str] = None
    cover_document_version: Optional[int] = None
    qa_report_id: Optional[str] = None
    qa_report_summary: Optional[Dict[str, Any]] = None
    approval_attestation: str
    created_at: datetime
    invalidated_at: Optional[datetime] = None
    invalidation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalVerificationResult(BaseModel):
    is_valid: bool
    active_snapshot: Optional[ApprovalSnapshotResponse] = None
    hash_match: bool
    current_hashes: Dict[str, Optional[str]]
    divergences: List[str] = Field(default_factory=list)
    remediation: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalHistoryResponse(BaseModel):
    items: List[ApprovalSnapshotResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)

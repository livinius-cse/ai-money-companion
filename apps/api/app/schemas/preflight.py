from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class QAFinding(BaseModel):
    rule_id: str = Field(..., description="Stable rule identifier, e.g. QA-INT-002")
    category: Literal["MANUSCRIPT", "INTERIOR", "COVER", "METADATA"]
    severity: Literal["BLOCKING", "WARNING", "INFO"]
    explanation: str
    relevant_field: str
    observed_value: Any = None
    remediation: str

    model_config = ConfigDict(from_attributes=True)


class CryptographicHashes(BaseModel):
    manuscript_hash: Optional[str] = None
    metadata_hash: Optional[str] = None
    interior_hash: Optional[str] = None
    cover_hash: Optional[str] = None
    composite_hash: Optional[str] = None
    hash_scheme_version: str = "kdp-sha256-v1"

    model_config = ConfigDict(from_attributes=True)


class DocumentVersionInfo(BaseModel):
    interior_id: Optional[str] = None
    interior_version: Optional[int] = None
    interior_page_count: Optional[int] = None
    interior_file_size: Optional[int] = None
    cover_id: Optional[str] = None
    cover_version: Optional[int] = None
    cover_file_size: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class PreFlightQAReport(BaseModel):
    report_id: str
    book_id: str
    book_title: str
    timestamp: datetime
    is_ready_for_approval: bool
    blocking_count: int
    warning_count: int
    info_count: int
    findings: List[QAFinding]
    hashes: CryptographicHashes
    document_versions: DocumentVersionInfo
    ai_disclosure_attested: bool
    readability_summary: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

import hashlib
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.sales import SalesImportBatch, SalesRecord
from app.schemas.recommendation import (
    BusinessRecommendationResponse,
    RecommendationItem,
)
from app.schemas.sales import (
    CurrencyBreakdown,
    FormatBreakdown,
    MarketplaceBreakdown,
    SalesAnalyticsSummary,
    SalesProvenance,
    SalesReportType,
)

DEMO_DISCLAIMER = "DEMO DATA — NOT REAL KDP EARNINGS"


def _recommendation_id(
    report_type: SalesReportType,
    provenance: SalesProvenance,
    title: str,
    evidence: str,
) -> str:
    digest = hashlib.sha256(
        f"{report_type}|{provenance}|{title}|{evidence}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{report_type.lower()}-{provenance.lower()}-{digest}"


class SalesAnalyticsService:
    @classmethod
    def get_summary(
        cls,
        db: Session,
        book: Book,
        owner_id: str,
        report_type: SalesReportType,
        provenance: SalesProvenance,
    ) -> SalesAnalyticsSummary:
        records = list(
            db.scalars(
                select(SalesRecord)
                .where(
                    SalesRecord.owner_id == owner_id,
                    SalesRecord.book_id == book.id,
                    SalesRecord.report_type == report_type,
                    SalesRecord.provenance == provenance,
                )
                .order_by(SalesRecord.transaction_date.asc(), SalesRecord.id.asc())
            ).all()
        )
        valid_batches = list(
            db.scalars(
                select(SalesImportBatch)
                .where(
                    SalesImportBatch.owner_id == owner_id,
                    SalesImportBatch.book_id == book.id,
                    SalesImportBatch.report_type == report_type,
                    SalesImportBatch.provenance == provenance,
                    SalesImportBatch.status == "VALID",
                )
            ).all()
        )

        by_currency: Dict[str, List[SalesRecord]] = {}
        by_marketplace: Dict[str, List[SalesRecord]] = {}
        by_format: Dict[str, List[SalesRecord]] = {}
        for record in records:
            if record.currency:
                by_currency.setdefault(record.currency, []).append(record)
            by_marketplace.setdefault(record.marketplace, []).append(record)
            by_format.setdefault(record.format or "", []).append(record)

        royalty_totals = [
            CurrencyBreakdown(
                currency=currency,
                reported_royalties=round(
                    sum(record.royalty_amount or 0.0 for record in currency_records),
                    2,
                ),
            )
            for currency, currency_records in sorted(by_currency.items())
            if report_type == "PRIOR_MONTH_ROYALTIES"
        ]
        marketplace_breakdown = []
        for marketplace, rows in sorted(by_marketplace.items()):
            royalties_by_currency: Dict[str, float] = {}
            if report_type == "PRIOR_MONTH_ROYALTIES":
                for currency, currency_rows in by_currency.items():
                    marketplace_rows = [
                        row for row in currency_rows if row.marketplace == marketplace
                    ]
                    if marketplace_rows:
                        royalties_by_currency[currency] = round(
                            sum(row.royalty_amount or 0.0 for row in marketplace_rows),
                            2,
                        )
            marketplace_breakdown.append(
                MarketplaceBreakdown(
                    marketplace=marketplace,
                    paid_units=sum(row.paid_units for row in rows),
                    free_units=sum(row.free_units for row in rows),
                    kenp_read_pages=sum(row.kenp_read_pages for row in rows),
                    royalties_by_currency=royalties_by_currency,
                )
            )

        format_breakdown = [
            FormatBreakdown(
                format=format_name or None,
                paid_units=sum(row.paid_units for row in rows),
                free_units=sum(row.free_units for row in rows),
            )
            for format_name, rows in sorted(by_format.items())
        ]
        periods = sorted({record.transaction_date[:7] for record in records})
        dates = [record.transaction_date for record in records]
        is_demo = provenance == "SIMULATED_DEMO"
        return SalesAnalyticsSummary(
            report_type=report_type,
            provenance=provenance,
            is_demo=is_demo,
            demo_disclaimer=DEMO_DISCLAIMER if is_demo else None,
            total_paid_units=sum(record.paid_units for record in records),
            total_free_units=sum(record.free_units for record in records),
            total_kenp_read_pages=sum(record.kenp_read_pages for record in records),
            transaction_count=len(records),
            batch_count=len(valid_batches),
            royalty_totals=royalty_totals,
            marketplace_breakdown=marketplace_breakdown,
            format_breakdown=format_breakdown,
            reporting_periods=periods,
            earliest_date=min(dates) if dates else None,
            latest_date=max(dates) if dates else None,
        )

    @classmethod
    def get_recommendations(
        cls,
        db: Session,
        book: Book,
        owner_id: str,
        report_type: SalesReportType,
        provenance: SalesProvenance,
    ) -> BusinessRecommendationResponse:
        summary = cls.get_summary(db, book, owner_id, report_type, provenance)
        recommendations: List[RecommendationItem] = []

        if summary.transaction_count:
            if report_type == "ORDERS":
                evidence = (
                    f"Imported Orders reports contain {summary.transaction_count} rows, "
                    f"{summary.total_paid_units} paid units, and "
                    f"{summary.total_free_units} free units across "
                    f"{len(summary.reporting_periods)} reporting period(s)."
                )
            elif report_type == "KENP_READ":
                evidence = (
                    f"Imported KENP Read reports contain {summary.transaction_count} rows "
                    f"and {summary.total_kenp_read_pages} reported KENP pages read across "
                    f"{len(summary.reporting_periods)} reporting period(s)."
                )
            else:
                royalties = "; ".join(
                    f"{item.currency} {item.reported_royalties:.2f}"
                    for item in summary.royalty_totals
                )
                evidence = (
                    f"Imported Prior Month's Royalties reports contain "
                    f"{summary.transaction_count} rows with reported royalties "
                    f"{royalties or 'not available'} across "
                    f"{len(summary.reporting_periods)} reporting period(s). "
                    "Currencies are reported separately without conversion."
                )
            recommendations.append(
                RecommendationItem(
                    id=_recommendation_id(
                        report_type,
                        provenance,
                        "Report summary",
                        evidence,
                    ),
                    title=f"Review {report_type.replace('_', ' ').title()} activity",
                    category="SALES_PERFORMANCE",
                    supporting_evidence=evidence,
                    suggested_action=(
                        "Review the original report and confirm the mapped columns before "
                        "making publishing decisions."
                    ),
                    provenance=provenance,
                )
            )

        is_demo = provenance == "SIMULATED_DEMO"
        return BusinessRecommendationResponse(
            book_id=book.id,
            book_title=book.title,
            total_recommendations=len(recommendations),
            recommendations=recommendations,
            data_sources_evaluated=[
                f"{report_type} report data ({provenance})",
                "Persisted book metadata",
            ],
            demo_disclaimer=DEMO_DISCLAIMER if is_demo else None,
            disclaimer=(
                "Historical report observations only. They do not predict or guarantee "
                "future royalties or performance."
            ),
        )

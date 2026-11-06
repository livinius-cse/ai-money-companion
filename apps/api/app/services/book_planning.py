from typing import Optional
from app.ai.factory import AIProviderFactory
from app.schemas.planning import BookPlanRequest, BookPlanResponse
from app.schemas.kdp_validator import PrintSpecsValidationRequest
from app.services.kdp_validator import KDPValidatorService


class BookPlanningService:
    """
    Domain service for structured book proposals, chapter breakdowns, and page budgets.
    Performs pure page calculation math and delegates page-count limits to KDPValidatorService.
    """

    @staticmethod
    async def plan_book(request: BookPlanRequest) -> BookPlanResponse:
        prompt = (
            f"Generate a structured publishing plan for a book with topic: '{request.topic}', "
            f"target audience: '{request.target_audience}', book type: '{request.book_type}', "
            f"format: '{request.print_format}', trim size: '{request.target_trim_size}', "
            f"paper: '{request.paper_type}', target page budget: {request.target_pages} pages."
        )

        # Execute structured generation through configured AI provider
        envelope = await AIProviderFactory.execute_structured(
            prompt=prompt,
            response_model=BookPlanResponse,
            system_prompt="You are a professional book packaging architect and KDP publishing strategist.",
        )
        plan = envelope.data

        # 1. Pure page calculation math (Front matter + Chapter pages + Back matter)
        calculated_pages = plan.front_matter_pages + sum(c.allocated_pages for c in plan.chapters) + plan.back_matter_pages
        plan.total_calculated_pages = calculated_pages
        plan.is_odd_page_count = (calculated_pages % 2 != 0)

        # 2. Manufacturing parity notice (No barcode claims)
        if plan.is_odd_page_count:
            plan.kdp_manufacturing_notice = (
                "KDP rounds an odd interior page count up to the nearest even number of whole sheets."
            )
        else:
            plan.kdp_manufacturing_notice = None

        # 3. Delegate page-count limits to KDPValidatorService
        val_req = PrintSpecsValidationRequest(
            print_format=request.print_format,
            trim_size=request.target_trim_size,
            paper_type=request.paper_type,
            page_count=calculated_pages,
            marketplace=request.marketplace,
        )
        val_result = KDPValidatorService.validate_print_specs(val_req)

        # If blocking errors exist, raise ValueError with explicit details
        if not val_result.is_valid:
            err_details = "; ".join(e.message for e in val_result.blocking_errors)
            raise ValueError(f"Book plan exceeds verified KDP specification limits: {err_details}")

        if val_result.matched_specification:
            plan.specification_matched = True
            plan.spec_id = val_result.matched_specification.get("spec_id")
            plan.specification_advisory = None
        else:
            plan.specification_matched = False
            plan.spec_id = None
            if val_result.advisory_warnings:
                plan.specification_advisory = "; ".join(w.message for w in val_result.advisory_warnings)

        return plan

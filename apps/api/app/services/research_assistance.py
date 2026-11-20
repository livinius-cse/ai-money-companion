import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.factory import AIProviderFactory
from app.models.book import Book
from app.models.chapter import Chapter
from app.schemas.research import (
    ResearchAssistanceRequest,
    ResearchAssistanceResponse,
)


class ResearchAssistanceService:
    @classmethod
    async def assist(
        cls,
        db: Session,
        book: Book,
        request: ResearchAssistanceRequest,
    ) -> ResearchAssistanceResponse:
        chapter_titles = list(
            db.scalars(
                select(Chapter.title)
                .where(
                    Chapter.book_id == book.id,
                    Chapter.owner_id == book.owner_id,
                )
                .order_by(Chapter.chapter_number.asc())
            ).all()
        )
        persisted_context = {
            "title": book.title,
            "subtitle": book.subtitle,
            "topic": book.topic,
            "concept": book.book_concept,
            "target_audience": book.target_audience,
            "reader_profile": book.target_reader_profile,
            "chapter_titles": chapter_titles,
            "requested_focus": request.focus_topic,
            "reader_question": request.target_reader_question,
        }
        prompt = (
            "Provide editorial research assistance for this book using only the supplied context. "
            "Clearly label generated output as suggestions or assumptions. Do not claim to have "
            "performed external research. Do not invent sales demand, keyword volumes, rankings, "
            "competitors, reviews, citations, URLs, or market statistics. Suggest questions the "
            "author can investigate, not factual answers that require external evidence. "
            "Return title/subtitle/keyword/category ideas only as unverified editorial suggestions. "
            "Do not repeat prompt instructions as book facts.\n\n"
            f"Book context:\n{json.dumps(persisted_context, ensure_ascii=False)}"
        )
        response = await AIProviderFactory.execute_structured(
            prompt=prompt,
            response_model=ResearchAssistanceResponse,
            system_prompt=(
                "You are a publishing editorial assistant. Never represent assumptions as "
                "verified external facts and never fabricate market evidence."
            ),
        )

        result = response.data
        result.book_id = book.id
        result.facts = [
            f"Persisted title: {book.title}",
            f"Persisted topic: {book.topic}",
            f"Persisted chapter titles: {len(chapter_titles)}",
        ]
        result.missing_external_research = [
            "No external demand, keyword-volume, ranking, competitor, review, citation, or market research was performed."
        ]
        return result

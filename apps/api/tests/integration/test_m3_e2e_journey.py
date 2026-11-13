import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.security import get_password_hash, generate_csrf_token
from app.models.user import User


def get_auth_headers(client: TestClient, user: User) -> dict:
    login_csrf = generate_csrf_token(identity="anonymous")
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "StrongPassword123!"},
        headers={"X-CSRF-Token": login_csrf, "Origin": "http://localhost:3000"},
    )
    assert login_res.status_code == 200
    user_csrf = login_res.cookies["csrf_token"]
    return {
        "X-CSRF-Token": user_csrf,
        "Origin": "http://localhost:3000",
    }


def test_complete_m3_user_journey(client: TestClient, test_user: User):
    """
    Complete 15-step End-to-End User Journey:
    1. Authenticate.
    2. Create a new book.
    3. Complete book concept.
    4. Generate a page plan using MockAIProvider.
    5. Save the plan.
    6. Create and reorder chapters.
    7. Edit and save Markdown content.
    8. Generate a chapter draft.
    9. Edit the generated draft.
    10. Create an illustration prompt.
    11. Create a placeholder.
    12. Upload an image.
    13. Mark it GENERATED.
    14. Explicitly approve it.
    15. Reload the book and verify all data persists.
    """
    # -------------------------------------------------------------
    # Step 1: Authenticate
    # -------------------------------------------------------------
    headers = get_auth_headers(client, test_user)

    # -------------------------------------------------------------
    # Step 2: Create a new book
    # -------------------------------------------------------------
    create_payload = {
        "title": "The Zero-Debt Formula",
        "subtitle": "A Step-by-Step System to Financial Freedom",
        "topic": "Personal Finance, Debt Elimination, Cash Flow Automation",
        "target_audience": "Working professionals aged 25-40",
        "target_reader_profile": "Earns steady income, feels trapped by monthly minimums.",
        "book_type": "non_fiction",
        "print_format": "paperback",
        "marketplace": "amazon_com",
        "trim_size": "6x9",
        "paper_type": "white_bw",
        "target_page_count": 120,
    }
    create_res = client.post("/api/v1/books", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    book = create_res.json()
    book_id = book["id"]
    assert book["title"] == "The Zero-Debt Formula"
    assert book["status"] == "DRAFT"

    # -------------------------------------------------------------
    # Step 3: Complete book concept
    # -------------------------------------------------------------
    concept_update = {
        "book_concept": "Combines behavioral psychology with mathematical payoff acceleration.",
        "status": "PLANNING",
    }
    update_res = client.put(f"/api/v1/books/{book_id}", json=concept_update, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "PLANNING"
    assert update_res.json()["book_concept"] == concept_update["book_concept"]

    # -------------------------------------------------------------
    # Step 4: Generate a page plan using MockAIProvider
    # -------------------------------------------------------------
    plan_res = client.post(f"/api/v1/books/{book_id}/plan/generate", headers=headers)
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert len(plan["chapters"]) >= 3
    assert len(plan["title_options"]) >= 1

    # -------------------------------------------------------------
    # Step 5: Save the plan
    # -------------------------------------------------------------
    apply_payload = {
        "selected_title": plan["title_options"][0],
        "selected_subtitle": plan["subtitle_options"][0],
        "target_reader_avatar": plan["target_reader_avatar"],
        "front_matter_pages": plan["front_matter_pages"],
        "back_matter_pages": plan["back_matter_pages"],
        "chapters": plan["chapters"],
    }
    apply_res = client.post(f"/api/v1/books/{book_id}/plan/apply", json=apply_payload, headers=headers)
    assert apply_res.status_code == 200
    applied_book = apply_res.json()
    assert applied_book["chapter_count"] == len(plan["chapters"])
    assert applied_book["status"] == "PLANNING"

    # -------------------------------------------------------------
    # Step 6: Create and reorder chapters
    # -------------------------------------------------------------
    # Fetch chapters
    chaps_res = client.get(f"/api/v1/books/{book_id}/chapters", headers=headers)
    assert chaps_res.status_code == 200
    chapters = chaps_res.json()
    chap1_id = chapters[0]["id"]
    chap2_id = chapters[1]["id"]

    # Add a custom bonus chapter
    bonus_chap_res = client.post(
        f"/api/v1/books/{book_id}/chapters",
        json={
            "chapter_number": len(chapters) + 1,
            "title": "Bonus Chapter: The Emergency Cash Buffer",
            "allocated_pages": 10,
        },
        headers=headers,
    )
    assert bonus_chap_res.status_code == 201
    bonus_chap_id = bonus_chap_res.json()["id"]

    # Reorder chapters (swap chap 1 and chap 2)
    reorder_payload = {
        "reordered_chapters": [
            {"chapter_id": chap1_id, "chapter_number": 2},
            {"chapter_id": chap2_id, "chapter_number": 1},
        ]
    }
    reorder_res = client.post(f"/api/v1/books/{book_id}/chapters/reorder", json=reorder_payload, headers=headers)
    assert reorder_res.status_code == 200
    reordered_list = reorder_res.json()
    assert reordered_list[0]["id"] == chap2_id
    assert reordered_list[0]["chapter_number"] == 1

    # -------------------------------------------------------------
    # Step 7: Edit and save Markdown content
    # -------------------------------------------------------------
    sample_md = (
        "# Taking Stock: The Baseline Reality Check\n\n"
        "Before you can direct your cash flow toward wealth, you must confront the baseline numbers. "
        "Financial anxiety thrives when numbers remain ambiguous and undefined.\n\n"
        "## Key Directives\n\n"
        "- Audit last 90 days of transactions.\n"
        "- Eliminate unused recurring subscriptions.\n"
        "- Establish a guilt-free automated spending split."
    )
    save_chap_res = client.put(
        f"/api/v1/books/{book_id}/chapters/{chap1_id}",
        json={"content": sample_md, "draft_status": "DRAFT"},
        headers=headers,
    )
    assert save_chap_res.status_code == 200
    chap1_saved = save_chap_res.json()
    assert chap1_saved["word_count"] > 20
    assert chap1_saved["estimated_reading_minutes"] >= 1

    # -------------------------------------------------------------
    # Step 8: Generate a chapter draft using AI
    # -------------------------------------------------------------
    draft_res = client.post(
        f"/api/v1/books/{book_id}/chapters/{chap2_id}/draft",
        json={"target_words": 1500, "tone": "authoritative_practical"},
        headers=headers,
    )
    assert draft_res.status_code == 200
    ai_draft = draft_res.json()
    assert ai_draft["is_draft"] is True
    assert ai_draft["author_reviewed"] is False
    assert len(ai_draft["markdown_content"]) > 100

    # Verify existing DB chapter content was NOT overwritten automatically
    chap2_check = client.get(f"/api/v1/books/{book_id}/chapters/{chap2_id}", headers=headers).json()
    assert chap2_check["content"] == ""

    # -------------------------------------------------------------
    # Step 9: Edit the generated draft & save
    # -------------------------------------------------------------
    user_edited_content = ai_draft["markdown_content"] + "\n\n## Author Addendum\nPersonal notes added during review."
    accept_draft_res = client.put(
        f"/api/v1/books/{book_id}/chapters/{chap2_id}",
        json={"content": user_edited_content, "draft_status": "COMPLETED"},
        headers=headers,
    )
    assert accept_draft_res.status_code == 200
    assert accept_draft_res.json()["draft_status"] == "COMPLETED"

    # -------------------------------------------------------------
    # Step 10: Create an illustration prompt
    # -------------------------------------------------------------
    ill_prompt_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={
            "chapter_id": chap1_id,
            "prompt": "Line-art debt snowball payoff chart, clean vectors, high contrast.",
            "style_preset": "modern_clean_vector",
            "status": "PROMPT",
        },
        headers=headers,
    )
    assert ill_prompt_res.status_code == 201
    prompt_ill = ill_prompt_res.json()
    assert prompt_ill["status"] == "PROMPT"

    # -------------------------------------------------------------
    # Step 11: Create a placeholder
    # -------------------------------------------------------------
    placeholder_res = client.post(
        f"/api/v1/books/{book_id}/illustrations",
        json={
            "chapter_id": chap2_id,
            "prompt": "Automated cash flow waterfall diagram.",
            "status": "PLACEHOLDER",
        },
        headers=headers,
    )
    assert placeholder_res.status_code == 201
    placeholder_ill = placeholder_res.json()
    placeholder_id = placeholder_ill["id"]
    assert placeholder_ill["status"] == "PLACEHOLDER"

    # -------------------------------------------------------------
    # Step 12: Upload an image
    # -------------------------------------------------------------
    valid_png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 300
    files = {"file": ("waterfall_chart.png", io.BytesIO(valid_png_bytes), "image/png")}
    upload_res = client.post(
        f"/api/v1/books/{book_id}/illustrations/{placeholder_id}/upload",
        files=files,
        headers={"X-CSRF-Token": headers["X-CSRF-Token"], "Origin": headers["Origin"]},
    )
    assert upload_res.status_code == 200
    uploaded_ill = upload_res.json()
    assert uploaded_ill["storage_key"] is not None
    assert uploaded_ill["sha256_hash"] is not None
    assert uploaded_ill["file_size_bytes"] == len(valid_png_bytes)

    # -------------------------------------------------------------
    # Step 13: Mark it GENERATED
    # -------------------------------------------------------------
    assert uploaded_ill["status"] == "GENERATED"
    assert uploaded_ill["asset_source"] == "MANUAL_UPLOAD"

    # -------------------------------------------------------------
    # Step 14: Explicitly approve it (APPROVED_FINAL)
    # -------------------------------------------------------------
    approve_res = client.patch(
        f"/api/v1/books/{book_id}/illustrations/{placeholder_id}/status",
        json={"status": "APPROVED_FINAL", "human_approved": True},
        headers=headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED_FINAL"

    # -------------------------------------------------------------
    # Step 15: Reload the book and verify all data persists
    # -------------------------------------------------------------
    final_book_res = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert final_book_res.status_code == 200
    final_book = final_book_res.json()
    assert final_book["id"] == book_id
    assert final_book["chapter_count"] == len(plan["chapters"]) + 1
    assert final_book["total_word_count"] > 100
    assert final_book["illustration_count"] == 2

    # Verify chapters persist
    final_chaps_res = client.get(f"/api/v1/books/{book_id}/chapters", headers=headers)
    assert final_chaps_res.status_code == 200
    final_chaps = final_chaps_res.json()
    assert len(final_chaps) == len(plan["chapters"]) + 1
    assert any(c["id"] == chap1_id and c["word_count"] > 20 for c in final_chaps)
    assert any(c["id"] == chap2_id and c["draft_status"] == "COMPLETED" for c in final_chaps)

    # Verify illustrations persist
    final_ills_res = client.get(f"/api/v1/books/{book_id}/illustrations", headers=headers)
    assert final_ills_res.status_code == 200
    final_ills = final_ills_res.json()
    assert len(final_ills) == 2
    approved_item = next(i for i in final_ills if i["id"] == placeholder_id)
    assert approved_item["status"] == "APPROVED_FINAL"

    # Verify asset stream retrieval
    asset_stream = client.get(f"/api/v1/books/{book_id}/illustrations/{placeholder_id}/asset", headers=headers)
    assert asset_stream.status_code == 200
    assert asset_stream.content == valid_png_bytes

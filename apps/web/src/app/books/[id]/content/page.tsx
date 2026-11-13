"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import { MarkdownPreview } from "@/components/markdown-preview";
import {
  PenTool,
  Save,
  Sparkles,
  Eye,
  Edit3,
  Columns,
  CheckCircle2,
  Clock,
  Plus,
  Trash2,
  Bold,
  Italic,
  Heading1,
  Heading2,
  List,
  Quote,
  X,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  print_format: string;
  trim_size: string;
  status: string;
}

interface Chapter {
  id: string;
  chapter_number: number;
  chapter_type: string;
  title: string;
  summary?: string | null;
  content: string;
  allocated_pages: number;
  word_count: number;
  estimated_reading_minutes: number;
  draft_status: string;
}

interface ManuscriptDraftResponse {
  chapter_title: string;
  markdown_content: string;
  word_count: number;
  estimated_reading_minutes: number;
  is_draft: boolean;
  author_reviewed: boolean;
}

export default function ContentStudioPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const bookId = params.id as string;
  const initialChapterId = searchParams.get("chapter");

  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedChapterId, setSelectedChapterId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Active chapter editing state
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [content, setContent] = useState("");
  const [draftStatus, setDraftStatus] = useState("DRAFT");
  const [allocatedPages, setAllocatedPages] = useState(10);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // View mode: "edit" | "preview" | "split"
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">("split");

  // AI Draft Modal state
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);
  const [draftTargetWords, setDraftTargetWords] = useState(1500);
  const [draftTone, setDraftTone] = useState("authoritative_practical");
  const [drafting, setDrafting] = useState(false);
  const [generatedDraft, setGeneratedDraft] = useState<ManuscriptDraftResponse | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && bookId) {
      loadBookAndChapters();
    }
  }, [isAuthenticated, bookId]);

  const loadBookAndChapters = async () => {
    try {
      setLoading(true);
      const [bookData, chaps] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<Chapter[]>(`/api/v1/books/${bookId}/chapters`),
      ]);
      setBook(bookData);
      setChapters(chaps || []);

      if (chaps && chaps.length > 0) {
        const target = initialChapterId
          ? chaps.find((c) => c.id === initialChapterId) || chaps[0]
          : chaps[0];
        selectChapter(target);
      }
    } catch (err) {
      console.error("Failed to load content studio:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectChapter = (chap: Chapter) => {
    if (hasUnsavedChanges) {
      if (!confirm("You have unsaved changes. Discard and switch chapter?")) {
        return;
      }
    }
    setSelectedChapterId(chap.id);
    setTitle(chap.title);
    setSummary(chap.summary || "");
    setContent(chap.content || "");
    setDraftStatus(chap.draft_status || "DRAFT");
    setAllocatedPages(chap.allocated_pages || 10);
    setHasUnsavedChanges(false);
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setHasUnsavedChanges(true);
  };

  const handleSaveChapter = async () => {
    if (!selectedChapterId) return;
    try {
      setSaving(true);
      const updated = await apiClient<Chapter>(
        `/api/v1/books/${bookId}/chapters/${selectedChapterId}`,
        {
          method: "PUT",
          body: JSON.stringify({
            title: title.trim(),
            summary: summary.trim() || null,
            content: content,
            draft_status: draftStatus,
            allocated_pages: allocatedPages,
          }),
        }
      );

      setChapters((prev) =>
        prev.map((c) => (c.id === selectedChapterId ? updated : c))
      );
      setHasUnsavedChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert("Failed to save chapter.");
    } finally {
      setSaving(false);
    }
  };

  const handleAddChapter = async () => {
    try {
      const nextNum = chapters.length + 1;
      const created = await apiClient<Chapter>(`/api/v1/books/${bookId}/chapters`, {
        method: "POST",
        body: JSON.stringify({
          chapter_number: nextNum,
          title: `Chapter ${nextNum}: New Topic`,
          allocated_pages: 10,
          content: "",
        }),
      });

      setChapters((prev) => [...prev, created]);
      selectChapter(created);
    } catch (err) {
      alert("Failed to add chapter.");
    }
  };

  const handleGenerateAIDraft = async () => {
    if (!selectedChapterId) return;
    try {
      setDrafting(true);
      const res = await apiClient<ManuscriptDraftResponse>(
        `/api/v1/books/${bookId}/chapters/${selectedChapterId}/draft`,
        {
          method: "POST",
          body: JSON.stringify({
            target_words: draftTargetWords,
            tone: draftTone,
          }),
        }
      );
      setGeneratedDraft(res);
    } catch (err) {
      alert("Failed to generate AI draft.");
    } finally {
      setDrafting(false);
    }
  };

  const applyGeneratedDraft = () => {
    if (!generatedDraft) return;
    setContent(generatedDraft.markdown_content);
    setHasUnsavedChanges(true);
    setIsDraftModalOpen(false);
    setGeneratedDraft(null);
  };

  const insertFormatting = (prefix: string, suffix: string = "") => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);

    const replacement = prefix + selectedText + suffix;
    const newContent = text.substring(0, start) + replacement + text.substring(end);

    setContent(newContent);
    setHasUnsavedChanges(true);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + prefix.length,
        start + prefix.length + selectedText.length
      );
    }, 0);
  };

  const words = content.trim() ? content.match(/\b\w+\b/g)?.length || 0 : 0;
  const readingTime = Math.max(1, Math.round(words / 200));

  if (authLoading || loading || !book) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      <BookSubNav
        bookId={book.id}
        bookTitle={book.title}
        status={book.status}
        printFormat={book.print_format}
        trimSize={book.trim_size}
      />

      {/* Content Studio Workspace */}
      <div className="flex-1 flex overflow-hidden max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Left Sidebar: Chapters Nav */}
        <aside className="w-72 shrink-0 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col overflow-hidden h-[calc(100vh-140px)]">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Chapters ({chapters.length})
            </h2>
            <button
              onClick={handleAddChapter}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-400 border border-slate-700 transition"
              title="Add Chapter"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-thin">
            {chapters.map((chap) => {
              const isSelected = chap.id === selectedChapterId;
              return (
                <button
                  key={chap.id}
                  onClick={() => selectChapter(chap)}
                  className={`w-full text-left p-3 rounded-xl transition flex flex-col gap-1 border ${
                    isSelected
                      ? "bg-amber-500/10 border-amber-500/50 text-white"
                      : "bg-slate-900 border-transparent hover:bg-slate-800/60 text-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono text-amber-400 font-bold">
                      #{chap.chapter_number}
                    </span>
                    <span className="text-[10px] text-slate-500 font-medium">
                      {chap.word_count || 0} wds
                    </span>
                  </div>
                  <p className="text-xs font-semibold line-clamp-1">{chap.title}</p>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Main Editor Center */}
        <div className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col overflow-hidden h-[calc(100vh-140px)]">
          {/* Top Editor Toolbar */}
          <div className="p-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4 bg-slate-900/80">
            {/* Title & Unsaved pill */}
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setHasUnsavedChanges(true);
                }}
                className="font-bold text-base text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-amber-500 focus:outline-none transition w-64 sm:w-80"
              />
              {hasUnsavedChanges && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                  Unsaved
                </span>
              )}
              {saveSuccess && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  Saved
                </span>
              )}
            </div>

            {/* Right actions: Word count, View toggles, Save & AI */}
            <div className="flex items-center gap-3 text-xs">
              <div className="text-slate-400 flex items-center gap-2">
                <span>{words.toLocaleString()} words</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  ~{readingTime} min
                </span>
              </div>

              {/* View Mode Buttons */}
              <div className="flex items-center bg-slate-800 p-0.5 rounded-lg border border-slate-700">
                <button
                  onClick={() => setViewMode("edit")}
                  className={`p-1.5 rounded transition ${viewMode === "edit" ? "bg-slate-700 text-white" : "text-slate-400"}`}
                  title="Editor Only"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setViewMode("split")}
                  className={`p-1.5 rounded transition ${viewMode === "split" ? "bg-slate-700 text-white" : "text-slate-400"}`}
                  title="Split View"
                >
                  <Columns className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setViewMode("preview")}
                  className={`p-1.5 rounded transition ${viewMode === "preview" ? "bg-slate-700 text-white" : "text-slate-400"}`}
                  title="Preview Only"
                >
                  <Eye className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* AI Draft Button */}
              <button
                onClick={() => {
                  setGeneratedDraft(null);
                  setIsDraftModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 transition shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Draft</span>
              </button>

              {/* Save Button */}
              <button
                onClick={handleSaveChapter}
                disabled={saving}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm shadow-amber-500/20 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? "Saving..." : "Save"}</span>
              </button>
            </div>
          </div>

          {/* Quick Formatting Toolbar (only when editing) */}
          {viewMode !== "preview" && (
            <div className="px-4 py-1.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center gap-1 text-slate-400">
              <button
                onClick={() => insertFormatting("# ")}
                className="p-1 hover:text-white rounded"
                title="Heading 1"
              >
                <Heading1 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => insertFormatting("## ")}
                className="p-1 hover:text-white rounded"
                title="Heading 2"
              >
                <Heading2 className="w-3.5 h-3.5" />
              </button>
              <span className="w-px h-3 bg-slate-800 mx-1" />
              <button
                onClick={() => insertFormatting("**", "**")}
                className="p-1 hover:text-white rounded"
                title="Bold"
              >
                <Bold className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => insertFormatting("*", "*")}
                className="p-1 hover:text-white rounded"
                title="Italic"
              >
                <Italic className="w-3.5 h-3.5" />
              </button>
              <span className="w-px h-3 bg-slate-800 mx-1" />
              <button
                onClick={() => insertFormatting("- ")}
                className="p-1 hover:text-white rounded"
                title="Bullet List"
              >
                <List className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => insertFormatting("> ")}
                className="p-1 hover:text-white rounded"
                title="Blockquote"
              >
                <Quote className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Editor Body */}
          <div className="flex-1 overflow-hidden flex">
            {/* Editor Pane */}
            {(viewMode === "edit" || viewMode === "split") && (
              <div
                className={`flex-1 h-full p-4 overflow-y-auto ${
                  viewMode === "split" ? "border-r border-slate-800" : ""
                }`}
              >
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={handleContentChange}
                  placeholder="Write your chapter in Markdown here..."
                  className="w-full h-full bg-transparent text-slate-100 placeholder-slate-600 font-mono text-sm leading-relaxed resize-none focus:outline-none"
                />
              </div>
            )}

            {/* Preview Pane */}
            {(viewMode === "preview" || viewMode === "split") && (
              <div className="flex-1 h-full p-6 overflow-y-auto bg-slate-950/40">
                <MarkdownPreview content={content} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AI Draft Modal */}
      {isDraftModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-white text-base">Generate AI Chapter Draft</h3>
              </div>
              <button
                onClick={() => setIsDraftModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Generates a structured manuscript draft using your book topic and chapter synopsis. AI material is marked as DRAFT and requires human review.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Words</label>
                <input
                  type="number"
                  min={500}
                  max={5000}
                  step={100}
                  value={draftTargetWords}
                  onChange={(e) => setDraftTargetWords(parseInt(e.target.value, 10))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Tone of Voice</label>
                <select
                  value={draftTone}
                  onChange={(e) => setDraftTone(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white"
                >
                  <option value="authoritative_practical">Authoritative & Practical</option>
                  <option value="conversational_engaging">Conversational & Engaging</option>
                  <option value="analytical_systematic">Analytical & Systematic</option>
                </select>
              </div>
            </div>

            {/* Generated Output Preview */}
            {generatedDraft && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold text-amber-400">
                  <span>Generated Draft Preview ({generatedDraft.word_count} words)</span>
                  <span className="text-[10px] bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                    UNCONFIRMED DRAFT
                  </span>
                </div>
                <div className="max-h-60 overflow-y-auto p-4 rounded-xl bg-slate-800/80 border border-slate-700 text-xs text-slate-300 font-mono">
                  {generatedDraft.markdown_content}
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setIsDraftModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Close
              </button>

              {generatedDraft ? (
                <button
                  onClick={applyGeneratedDraft}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow-sm"
                >
                  Review & Insert into Editor
                </button>
              ) : (
                <button
                  onClick={handleGenerateAIDraft}
                  disabled={drafting}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm disabled:opacity-50 flex items-center gap-2"
                >
                  {drafting && <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />}
                  <span>{drafting ? "Drafting..." : "Generate Draft"}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

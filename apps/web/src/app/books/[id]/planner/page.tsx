"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  Calendar,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Save,
  Check,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  subtitle?: string | null;
  topic: string;
  target_audience?: string | null;
  target_reader_profile?: string | null;
  print_format: string;
  trim_size: string;
  paper_type: string;
  target_page_count: number;
  status: string;
  front_matter_pages: number;
  back_matter_pages: number;
}

interface ChapterPlanItem {
  chapter_number: number;
  title: string;
  summary: string;
  key_takeaways: string[];
  estimated_word_count: number;
  allocated_pages: number;
}

interface BookPlanResponse {
  title_options: string[];
  subtitle_options: string[];
  target_reader_avatar: string;
  front_matter_pages: number;
  chapters: ChapterPlanItem[];
  back_matter_pages: number;
  total_calculated_pages: number;
  is_odd_page_count: boolean;
  kdp_manufacturing_notice?: string | null;
  specification_matched: boolean;
  spec_id?: string | null;
  specification_advisory?: string | null;
}

export default function BookPlannerPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [applying, setApplying] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Plan editing states
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedSubtitle, setSelectedSubtitle] = useState("");
  const [targetAvatar, setTargetAvatar] = useState("");
  const [frontMatter, setFrontMatter] = useState(4);
  const [backMatter, setBackMatter] = useState(2);
  const [chapters, setChapters] = useState<ChapterPlanItem[]>([]);
  const [planGenerated, setPlanGenerated] = useState(false);
  const [titleOptions, setTitleOptions] = useState<string[]>([]);
  const [subtitleOptions, setSubtitleOptions] = useState<string[]>([]);
  const [kdpNotice, setKdpNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && bookId) {
      loadInitialData();
    }
  }, [isAuthenticated, bookId]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [bookData, existingChapters] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<any[]>(`/api/v1/books/${bookId}/chapters`),
      ]);
      setBook(bookData);
      setSelectedTitle(bookData.title);
      setSelectedSubtitle(bookData.subtitle || "");
      setTargetAvatar(bookData.target_reader_profile || "");
      setFrontMatter(bookData.front_matter_pages || 4);
      setBackMatter(bookData.back_matter_pages || 2);

      if (existingChapters && existingChapters.length > 0) {
        setChapters(
          existingChapters.map((c) => ({
            chapter_number: c.chapter_number,
            title: c.title,
            summary: c.summary || "",
            key_takeaways: [],
            estimated_word_count: c.word_count || c.allocated_pages * 250,
            allocated_pages: c.allocated_pages,
          }))
        );
        setPlanGenerated(true);
      }
    } catch (err: any) {
      setError("Failed to load planner data.");
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePlan = async () => {
    try {
      setGenerating(true);
      setError(null);
      const plan = await apiClient<BookPlanResponse>(`/api/v1/books/${bookId}/plan/generate`, {
        method: "POST",
      });

      setTitleOptions(plan.title_options);
      setSubtitleOptions(plan.subtitle_options);
      setSelectedTitle(plan.title_options[0] || book?.title || "");
      setSelectedSubtitle(plan.subtitle_options[0] || "");
      setTargetAvatar(plan.target_reader_avatar);
      setFrontMatter(plan.front_matter_pages);
      setBackMatter(plan.back_matter_pages);
      setChapters(plan.chapters);
      setKdpNotice(plan.kdp_manufacturing_notice || null);
      setPlanGenerated(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate plan.");
    } finally {
      setGenerating(false);
    }
  };

  const handleApplyPlan = async () => {
    if (!selectedTitle.trim() || chapters.length === 0) {
      setError("Please ensure you have selected a title and at least one chapter.");
      return;
    }
    try {
      setApplying(true);
      setError(null);
      setSuccess(false);

      await apiClient(`/api/v1/books/${bookId}/plan/apply`, {
        method: "POST",
        body: JSON.stringify({
          selected_title: selectedTitle,
          selected_subtitle: selectedSubtitle || null,
          target_reader_avatar: targetAvatar || null,
          front_matter_pages: frontMatter,
          back_matter_pages: backMatter,
          chapters: chapters.map((c, i) => ({
            chapter_number: i + 1,
            title: c.title,
            summary: c.summary,
            key_takeaways: c.key_takeaways || [],
            estimated_word_count: c.estimated_word_count,
            allocated_pages: c.allocated_pages,
          })),
        }),
      });

      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to apply plan.");
    } finally {
      setApplying(false);
    }
  };

  const handleChapterChange = (index: number, field: string, value: any) => {
    setChapters((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleAddChapter = () => {
    setChapters((prev) => [
      ...prev,
      {
        chapter_number: prev.length + 1,
        title: `Chapter ${prev.length + 1}: New Topic`,
        summary: "Chapter summary and key concepts.",
        key_takeaways: [],
        estimated_word_count: 2500,
        allocated_pages: 12,
      },
    ]);
  };

  const handleRemoveChapter = (index: number) => {
    setChapters((prev) => prev.filter((_, i) => i !== index));
  };

  const totalCalculatedPages =
    frontMatter + chapters.reduce((acc, c) => acc + (Number(c.allocated_pages) || 0), 0) + backMatter;
  const isOddPages = totalCalculatedPages % 2 !== 0;

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
        bookTitle={selectedTitle || book.title}
        status={book.status}
        printFormat={book.print_format}
        trimSize={book.trim_size}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Action Strip */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Calendar className="w-5 h-5 text-amber-500" />
              <span>Page Planning & Budgeting</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Structure chapters, allocate page limits, and ensure Amazon KDP page-count compliance.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleGeneratePlan}
              disabled={generating}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{generating ? "Generating Plan..." : "Generate Plan with AI"}</span>
            </button>
            <button
              onClick={handleApplyPlan}
              disabled={applying || chapters.length === 0}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{applying ? "Applying..." : "Save Plan to Studio"}</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Plan successfully saved and applied to Product Studio!</span>
          </div>
        )}

        {/* Page Budget Summary Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Total Planned Pages
            </span>
            <p className="text-2xl font-bold text-white mt-1">
              {totalCalculatedPages}
              <span className="text-xs text-slate-400 font-normal ml-1">pages</span>
            </p>
            <p className="text-[11px] text-slate-500">Target: {book.target_page_count} pgs</p>
          </div>

          <div>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Front / Back Matter
            </span>
            <p className="text-2xl font-bold text-slate-200 mt-1">
              {frontMatter} <span className="text-xs text-slate-500 font-normal">/</span> {backMatter}
            </p>
            <p className="text-[11px] text-slate-500">6 total matter pages</p>
          </div>

          <div>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              Chapter Count
            </span>
            <p className="text-2xl font-bold text-slate-200 mt-1">{chapters.length}</p>
            <p className="text-[11px] text-slate-500">Sequenced chapters</p>
          </div>

          <div>
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              KDP Manufacturing
            </span>
            <div className="mt-1">
              {isOddPages ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-semibold">
                  Odd ({totalCalculatedPages}) → Rounds Up
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
                  Even Parity Valid ({totalCalculatedPages})
                </span>
              )}
            </div>
            {isOddPages && (
              <p className="text-[10px] text-amber-400/80 mt-1">
                KDP rounds odd page counts to even sheet count.
              </p>
            )}
          </div>
        </div>

        {/* AI Suggested Titles & Subtitles (if generated) */}
        {titleOptions.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              AI Suggested Title & Subtitle Options
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs text-slate-300 font-semibold">Title Options</label>
                {titleOptions.map((opt, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedTitle(opt)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                      selectedTitle === opt
                        ? "bg-amber-500/10 border-amber-500 text-white font-semibold"
                        : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <span>{opt}</span>
                    {selectedTitle === opt && <Check className="w-3.5 h-3.5 text-amber-400" />}
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-300 font-semibold">Subtitle Options</label>
                {subtitleOptions.map((opt, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedSubtitle(opt)}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition flex items-center justify-between ${
                      selectedSubtitle === opt
                        ? "bg-amber-500/10 border-amber-500 text-white font-semibold"
                        : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-800"
                    }`}
                  >
                    <span>{opt}</span>
                    {selectedSubtitle === opt && <Check className="w-3.5 h-3.5 text-amber-400" />}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Chapters Table Editor */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Chapter Breakdown & Page Allocations</span>
            </h2>

            <button
              onClick={handleAddChapter}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Chapter</span>
            </button>
          </div>

          {chapters.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm border border-dashed border-slate-800 rounded-xl">
              No chapters in plan. Click "Generate Plan with AI" above to generate a complete outline.
            </div>
          ) : (
            <div className="space-y-3">
              {chapters.map((chap, idx) => (
                <div
                  key={idx}
                  className="bg-slate-800/50 border border-slate-800 rounded-xl p-4 space-y-3"
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                      <span className="w-6 h-6 rounded-md bg-amber-500/10 text-amber-400 text-xs font-bold flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <input
                        type="text"
                        value={chap.title}
                        onChange={(e) => handleChapterChange(idx, "title", e.target.value)}
                        placeholder="Chapter Title"
                        className="font-semibold text-sm text-white bg-transparent border-b border-transparent hover:border-slate-700 focus:border-amber-500 focus:outline-none transition w-full sm:w-80"
                      />
                    </div>

                    <div className="flex items-center gap-4 text-xs w-full sm:w-auto justify-between sm:justify-end">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Pages:</span>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={chap.allocated_pages}
                          onChange={(e) =>
                            handleChapterChange(idx, "allocated_pages", parseInt(e.target.value, 10) || 1)
                          }
                          className="w-16 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white text-center focus:outline-none focus:border-amber-500"
                        />
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Target Words:</span>
                        <input
                          type="number"
                          min={100}
                          max={25000}
                          step={100}
                          value={chap.estimated_word_count}
                          onChange={(e) =>
                            handleChapterChange(idx, "estimated_word_count", parseInt(e.target.value, 10) || 100)
                          }
                          className="w-20 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-white text-center focus:outline-none focus:border-amber-500"
                        />
                      </div>

                      <button
                        onClick={() => handleRemoveChapter(idx)}
                        className="text-slate-500 hover:text-rose-400 transition"
                        title="Delete Chapter"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <textarea
                    rows={2}
                    value={chap.summary}
                    onChange={(e) => handleChapterChange(idx, "summary", e.target.value)}
                    placeholder="Chapter synopsis, topics covered, and key reader takeaways..."
                    className="w-full px-3 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

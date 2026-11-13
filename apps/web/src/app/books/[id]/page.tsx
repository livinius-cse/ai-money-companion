"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  Compass,
  FileText,
  Calendar,
  PenTool,
  Image as ImageIcon,
  CheckCircle2,
  Clock,
  ArrowRight,
  BookOpen,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  subtitle?: string | null;
  topic: string;
  target_audience?: string | null;
  target_reader_profile?: string | null;
  book_type: string;
  print_format: string;
  marketplace: string;
  trim_size: string;
  paper_type: string;
  target_page_count: number;
  status: string;
  chapter_count: number;
  total_allocated_pages: number;
  total_word_count: number;
  illustration_count: number;
}

interface Chapter {
  id: string;
  chapter_number: number;
  title: string;
  summary?: string | null;
  allocated_pages: number;
  word_count: number;
  draft_status: string;
}

export default function BookOverviewPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);

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
      const [bookData, chapData] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<Chapter[]>(`/api/v1/books/${bookId}/chapters`),
      ]);
      setBook(bookData);
      setChapters(chapData || []);
    } catch (err) {
      console.error("Failed to load book overview:", err);
    } finally {
      setLoading(false);
    }
  };

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

  const estReadingMinutes = Math.max(1, Math.round(book.total_word_count / 200));

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

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Header */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-xs text-amber-400 font-semibold uppercase tracking-wider">
                Product Studio Project Hub
              </span>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {book.title}
              </h1>
              {book.subtitle && (
                <p className="text-sm text-slate-300 italic">{book.subtitle}</p>
              )}
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push(`/books/${book.id}/planner`)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm shadow-amber-500/20"
              >
                Page Planner
              </button>
              <button
                onClick={() => router.push(`/books/${book.id}/content`)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition"
              >
                Content Studio
              </button>
            </div>
          </div>

          <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">
            {book.topic}
          </p>
        </div>

        {/* 4 Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span>Page Budget</span>
            </span>
            <p className="text-2xl font-bold text-white">
              {book.total_allocated_pages || book.target_page_count}
              <span className="text-xs text-slate-500 font-normal ml-1">pages</span>
            </p>
            <p className="text-[11px] text-slate-500">Target: {book.target_page_count} pgs</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <PenTool className="w-3.5 h-3.5 text-cyan-400" />
              <span>Manuscript</span>
            </span>
            <p className="text-2xl font-bold text-white">
              {book.total_word_count.toLocaleString()}
              <span className="text-xs text-slate-500 font-normal ml-1">words</span>
            </p>
            <p className="text-[11px] text-slate-500">~{estReadingMinutes} min read time</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-purple-400" />
              <span>Structure</span>
            </span>
            <p className="text-2xl font-bold text-white">{book.chapter_count}</p>
            <p className="text-[11px] text-slate-500">Chapters configured</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <ImageIcon className="w-3.5 h-3.5 text-emerald-400" />
              <span>Illustrations</span>
            </span>
            <p className="text-2xl font-bold text-white">{book.illustration_count}</p>
            <p className="text-[11px] text-slate-500">Assets & Placeholders</p>
          </div>
        </div>

        {/* Workstream Quick-Access Panels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Studio Panel 1: Concept & Positioning */}
          <div
            onClick={() => router.push(`/books/${book.id}/concept`)}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
                  <FileText className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-white group-hover:text-amber-400 transition">
                  Book Concept & Audience
                </h3>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-1 transition" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Refine your target audience, reader avatar, category, and core value proposition.
            </p>
            <div className="pt-2 text-xs text-slate-500 flex items-center gap-2">
              <span className="font-medium text-slate-300">Audience:</span>
              <span className="truncate">{book.target_audience || "Not configured yet"}</span>
            </div>
          </div>

          {/* Studio Panel 2: Page Planner */}
          <div
            onClick={() => router.push(`/books/${book.id}/planner`)}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                  <Calendar className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-white group-hover:text-cyan-400 transition">
                  Page Planning & Budgeting
                </h3>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generate structured chapter plans with AI, allocate page budgets, and verify KDP manufacturing constraints.
            </p>
            <div className="pt-2 text-xs text-slate-500 flex items-center gap-2">
              <span className="font-medium text-slate-300">Chapters:</span>
              <span>{book.chapter_count} allocated</span>
            </div>
          </div>

          {/* Studio Panel 3: Content Studio */}
          <div
            onClick={() => router.push(`/books/${book.id}/content`)}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
                  <PenTool className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-white group-hover:text-purple-400 transition">
                  Markdown Content Studio
                </h3>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-1 transition" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Write chapters in Markdown with live preview, word count estimation, and offline AI drafting assistance.
            </p>
            <div className="pt-2 text-xs text-slate-500 flex items-center gap-2">
              <span className="font-medium text-slate-300">Drafted Words:</span>
              <span>{book.total_word_count.toLocaleString()} words</span>
            </div>
          </div>

          {/* Studio Panel 4: Illustration Studio */}
          <div
            onClick={() => router.push(`/books/${book.id}/illustrations`)}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-md"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                  <ImageIcon className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-white group-hover:text-emerald-400 transition">
                  Illustration Studio
                </h3>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition" />
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Generate cohesive prompts, create layout placeholders, upload private image assets, and approve final visuals.
            </p>
            <div className="pt-2 text-xs text-slate-500 flex items-center gap-2">
              <span className="font-medium text-slate-300">Visual Assets:</span>
              <span>{book.illustration_count} configured</span>
            </div>
          </div>
        </div>

        {/* Chapters Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-base text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-amber-500" />
              <span>Chapter Breakdown</span>
            </h3>
            <button
              onClick={() => router.push(`/books/${book.id}/content`)}
              className="text-xs text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1"
            >
              <span>Open in Content Studio</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {chapters.length === 0 ? (
            <div className="py-8 text-center text-slate-500 text-sm">
              No chapters planned yet. Launch the{" "}
              <button
                onClick={() => router.push(`/books/${book.id}/planner`)}
                className="text-amber-400 underline font-medium hover:text-amber-300"
              >
                Page Planner
              </button>{" "}
              to generate a structured table of contents.
            </div>
          ) : (
            <div className="divide-y divide-slate-800/80">
              {chapters.map((chap) => (
                <div
                  key={chap.id}
                  onClick={() => router.push(`/books/${book.id}/content?chapter=${chap.id}`)}
                  className="py-3 flex items-center justify-between gap-4 hover:bg-slate-800/30 px-3 rounded-lg cursor-pointer transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-white">
                      {chap.chapter_number}
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-white">{chap.title}</p>
                      {chap.summary && (
                        <p className="text-xs text-slate-400 line-clamp-1">{chap.summary}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span>{chap.allocated_pages} pgs</span>
                    <span>{chap.word_count} words</span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                        chap.draft_status === "COMPLETED"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : chap.draft_status === "DRAFT" || chap.draft_status === "IN_PROGRESS"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          : "bg-slate-800 text-slate-500 border-slate-700"
                      }`}
                    >
                      {chap.draft_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

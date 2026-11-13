"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import { FileText, Save, CheckCircle2 } from "lucide-react";

interface Book {
  id: string;
  title: string;
  subtitle?: string | null;
  topic: string;
  book_concept?: string | null;
  target_audience?: string | null;
  target_reader_profile?: string | null;
  book_type: string;
  print_format: string;
  marketplace: string;
  trim_size: string;
  paper_type: string;
  target_page_count: number;
  status: string;
}

export default function BookConceptPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [topic, setTopic] = useState("");
  const [bookConcept, setBookConcept] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [targetReaderProfile, setTargetReaderProfile] = useState("");
  const [bookType, setBookType] = useState("non_fiction");
  const [printFormat, setPrintFormat] = useState("paperback");
  const [trimSize, setTrimSize] = useState("6x9");
  const [paperType, setPaperType] = useState("white_bw");
  const [targetPageCount, setTargetPageCount] = useState(120);
  const [status, setStatus] = useState("DRAFT");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && bookId) {
      loadBook();
    }
  }, [isAuthenticated, bookId]);

  const loadBook = async () => {
    try {
      setLoading(true);
      const data = await apiClient<Book>(`/api/v1/books/${bookId}`);
      setBook(data);
      setTitle(data.title);
      setSubtitle(data.subtitle || "");
      setTopic(data.topic);
      setBookConcept(data.book_concept || "");
      setTargetAudience(data.target_audience || "");
      setTargetReaderProfile(data.target_reader_profile || "");
      setBookType(data.book_type);
      setPrintFormat(data.print_format);
      setTrimSize(data.trim_size);
      setPaperType(data.paper_type);
      setTargetPageCount(data.target_page_count);
      setStatus(data.status);
    } catch (err: any) {
      setError("Failed to load book concept.");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);

      const updated = await apiClient<Book>(`/api/v1/books/${bookId}`, {
        method: "PUT",
        body: JSON.stringify({
          title: title.trim(),
          subtitle: subtitle.trim() || null,
          topic: topic.trim(),
          book_concept: bookConcept.trim() || null,
          target_audience: targetAudience.trim() || null,
          target_reader_profile: targetReaderProfile.trim() || null,
          book_type: bookType,
          print_format: printFormat,
          trim_size: trimSize,
          paper_type: paperType,
          target_page_count: targetPageCount,
          status: status,
        }),
      });

      setBook(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to save changes.");
    } finally {
      setSaving(false);
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

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <FileText className="w-5 h-5 text-amber-500" />
              <span>Book Concept & Positioning</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Configure the foundational premise, audience persona, and physical KDP print specifications.
            </p>
          </div>

          {success && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Saved successfully!</span>
            </div>
          )}
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSave} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6">
          {/* Title & Topic */}
          <div className="space-y-4">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              1. Title & Value Proposition
            </h2>

            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Book Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Subtitle</label>
                <input
                  type="text"
                  value={subtitle}
                  onChange={(e) => setSubtitle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Core Topic & Premise *</label>
                <textarea
                  required
                  rows={3}
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Detailed Concept & Outline Notes
                </label>
                <textarea
                  rows={3}
                  value={bookConcept}
                  onChange={(e) => setBookConcept(e.target.value)}
                  placeholder="Additional background notes, chapter themes, or competitive differentiators."
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>
            </div>
          </div>

          {/* Reader Persona */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              2. Reader Persona & Audience
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Audience</label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Lifecycle Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="DRAFT">DRAFT</option>
                  <option value="PLANNING">PLANNING</option>
                  <option value="IN_PROGRESS">IN_PROGRESS</option>
                  <option value="READY">READY</option>
                  <option value="ARCHIVED">ARCHIVED</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Reader Profile / Avatar</label>
                <textarea
                  rows={2}
                  value={targetReaderProfile}
                  onChange={(e) => setTargetReaderProfile(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                />
              </div>
            </div>
          </div>

          {/* KDP Print Specifications */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              3. Amazon KDP Specifications
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Print Format</label>
                <select
                  value={printFormat}
                  onChange={(e) => setPrintFormat(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="paperback">Paperback</option>
                  <option value="hardcover">Hardcover</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Trim Size</label>
                <select
                  value={trimSize}
                  onChange={(e) => setTrimSize(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="6x9">6" x 9"</option>
                  <option value="5.5x8.5">5.5" x 8.5"</option>
                  <option value="5x8">5" x 8"</option>
                  <option value="7x10">7" x 10"</option>
                  <option value="8.5x11">8.5" x 11"</option>
                  <option value="8.25x8.25">8.25" x 8.25"</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Paper & Ink</label>
                <select
                  value={paperType}
                  onChange={(e) => setPaperType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="white_bw">Black & White (50# White)</option>
                  <option value="cream_bw">Black & White (55# Cream)</option>
                  <option value="groundwood_bw">Black & White (Groundwood)</option>
                  <option value="standard_color">Standard Color (White)</option>
                  <option value="premium_color">Premium Color (White)</option>
                </select>
              </div>

              <div className="sm:col-span-3">
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Page Budget: {targetPageCount} pages
                </label>
                <input
                  type="range"
                  min={30}
                  max={400}
                  step={2}
                  value={targetPageCount}
                  onChange={(e) => setTargetPageCount(parseInt(e.target.value, 10))}
                  className="w-full accent-amber-500"
                />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-md shadow-amber-500/20 disabled:opacity-50 flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? "Saving..." : "Save Changes"}</span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

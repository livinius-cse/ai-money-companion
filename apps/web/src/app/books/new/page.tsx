"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookOpen, Sparkles, ArrowLeft, CheckCircle2 } from "lucide-react";

export default function NewBookPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

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

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !topic.trim()) {
      setError("Please provide both a Title and a Core Topic.");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const res = await apiClient<{ id: string }>("/api/v1/books", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          subtitle: subtitle.trim() || null,
          topic: topic.trim(),
          book_concept: bookConcept.trim() || null,
          target_audience: targetAudience.trim() || null,
          target_reader_profile: targetReaderProfile.trim() || null,
          book_type: bookType,
          print_format: printFormat,
          marketplace: "amazon_com",
          trim_size: trimSize,
          paper_type: paperType,
          target_page_count: targetPageCount,
        }),
      });

      router.push(`/books/${res.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create book. Please check parameters.");
    } finally {
      setSaving(false);
    }
  };

  if (authLoading) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Back Link */}
        <button
          onClick={() => router.push("/books")}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Portfolio</span>
        </button>

        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-500" />
            <span>Create New Book Concept</span>
          </h1>
          <p className="text-sm text-slate-400">
            Define your book's premise, audience, and KDP manufacturing parameters to launch the Product Studio.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 space-y-6">
          {/* Section 1: Book Identity */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-amber-400 uppercase tracking-wider">
              1. Title & Positioning
            </h2>

            <div className="grid grid-cols-1 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Book Main Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. The 30-Day Money Reset"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Subtitle (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. A Practical Step-by-Step Budgeting and Debt Snowball Guide"
                  value={subtitle}
                  onChange={(e) => setSubtitle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Core Topic & Value Proposition *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe what the book is about, the specific problems it solves, and the unique mechanism it teaches."
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Audience & Persona */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h2 className="text-sm font-bold text-amber-400 uppercase tracking-wider">
              2. Target Reader & Audience
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Audience
                </label>
                <input
                  type="text"
                  placeholder="e.g. Working professionals aged 24-38"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Book Category / Type
                </label>
                <select
                  value={bookType}
                  onChange={(e) => setBookType(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="non_fiction">Non-Fiction / Guide</option>
                  <option value="workbook">Practical Workbook</option>
                  <option value="journal">Prompt Journal</option>
                  <option value="fiction">Fiction</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Reader Profile / Avatar
                </label>
                <textarea
                  rows={2}
                  placeholder="e.g. Mid-career professional earning a good income but feeling trapped by high living costs, seeking systematic cash flow automation."
                  value={targetReaderProfile}
                  onChange={(e) => setTargetReaderProfile(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
                />
              </div>
            </div>
          </div>

          {/* Section 3: KDP Print Specifications */}
          <div className="space-y-4 pt-4 border-t border-slate-800">
            <h2 className="text-sm font-bold text-amber-400 uppercase tracking-wider">
              3. Amazon KDP Print Specifications
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Print Format
                </label>
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
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Trim Size
                </label>
                <select
                  value={trimSize}
                  onChange={(e) => setTrimSize(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-800 border border-slate-700 text-sm text-white focus:outline-none focus:border-amber-500 transition"
                >
                  <option value="6x9">6" x 9" (Standard Trade)</option>
                  <option value="5.5x8.5">5.5" x 8.5" (Standard Digest)</option>
                  <option value="5x8">5" x 8" (Pocket Trade)</option>
                  <option value="7x10">7" x 10" (Textbook / Manual)</option>
                  <option value="8.5x11">8.5" x 11" (Workbook / Manual)</option>
                  <option value="8.25x8.25">8.25" x 8.25" (Square)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Paper & Ink
                </label>
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
                <p className="text-[11px] text-slate-500 mt-1">
                  KDP requires a minimum of 24 pages for paperback (75 for hardcover). Page budgets will be validated during planning.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="pt-6 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => router.push("/books")}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-md shadow-amber-500/20 disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />}
              <span>{saving ? "Creating Book..." : "Create Book & Open Studio"}</span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

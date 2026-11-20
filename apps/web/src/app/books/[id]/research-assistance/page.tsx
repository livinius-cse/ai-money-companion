"use client";

import React, { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { BookSubNav } from "@/components/book-sub-nav";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";

interface ResearchResult {
  topic_refinement: Array<{ angle_title: string; core_premise: string; differentiation_hook: string }>;
  audience_positioning: Record<string, unknown>;
  reader_profile_suggestions: Record<string, unknown>;
  metadata_suggestions: Record<string, unknown>;
  research_questions: Array<{ category: string; question: string; strategic_objective: string }>;
  content_gap_analysis: Array<{ missing_area: string; reader_expectation: string; suggested_chapter_or_section: string }>;
  publishing_preparation_checklist: string[];
  facts: string[];
  assumptions: string[];
  ai_suggestions: string[];
  missing_external_research: string[];
}

interface Book {
  id: string;
  title: string;
  status: string;
  print_format: string;
  trim_size: string;
}

export default function ResearchAssistancePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [focusTopic, setFocusTopic] = useState("");
  const [readerQuestion, setReaderQuestion] = useState("");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push("/login");
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && id) {
      void apiClient<Book>(`/api/v1/books/${id}`)
        .then(setBook)
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load book."));
    }
  }, [isAuthenticated, id]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient<ResearchResult>(`/api/v1/books/${id}/research-assistance`, {
        method: "POST",
        body: JSON.stringify({
          focus_topic: focusTopic || null,
          target_reader_question: readerQuestion || null,
        }),
      });
      setResult(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Research assistance is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      {book && <BookSubNav bookId={book.id} bookTitle={book.title} status={book.status} printFormat={book.print_format} trimSize={book.trim_size} />}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header>
          <p className="text-xs uppercase tracking-wider text-amber-400">AI-assisted · author verification required</p>
          <h1 className="text-3xl font-bold mt-1">Research assistance</h1>
          <p className="mt-2 text-sm text-slate-400">
            Get topic, audience, metadata, and research-question suggestions from the configured AI provider. External facts are not automatically researched.
          </p>
        </header>

        <form onSubmit={submit} className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <label className="block text-sm">
            Focus topic (optional)
            <input maxLength={300} value={focusTopic} onChange={(event) => setFocusTopic(event.target.value)} className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" />
          </label>
          <label className="block text-sm">
            Reader question (optional)
            <textarea maxLength={1000} rows={3} value={readerQuestion} onChange={(event) => setReaderQuestion(event.target.value)} className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" />
          </label>
          <button disabled={loading} className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-40">
            <Search className="h-4 w-4" /> {loading ? "Generating suggestions…" : "Generate assistance"}
          </button>
          {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
        </form>

        {result && (
          <>
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <h2 className="text-lg font-semibold">Verified persisted facts</h2>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">{result.facts.map((fact, index) => <li key={index}>{fact}</li>)}</ul>
            </section>
            <section className="grid gap-5 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">AI topic suggestions</h2>
                <ul className="mt-3 space-y-3 text-sm">{result.topic_refinement.map((angle, index) => (
                  <li key={index}><p className="font-medium">{angle.angle_title}</p><p className="mt-1 text-slate-300">{angle.core_premise}</p><p className="mt-1 text-xs text-slate-400">{angle.differentiation_hook}</p></li>
                ))}</ul>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">Audience and metadata suggestions</h2>
                <pre className="mt-3 whitespace-pre-wrap break-words text-xs text-slate-300">{JSON.stringify({ audience: result.audience_positioning, reader_profile: result.reader_profile_suggestions, metadata: result.metadata_suggestions }, null, 2)}</pre>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">Research questions and content gaps</h2>
                <ul className="mt-3 space-y-3 text-sm">{result.research_questions.map((item, index) => (
                  <li key={index}><p className="font-medium">{item.category}: {item.question}</p><p className="text-xs text-slate-400">{item.strategic_objective}</p></li>
                ))}</ul>
                <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-300">{result.content_gap_analysis.map((item, index) => <li key={index}>{item.missing_area}: {item.suggested_chapter_or_section}</li>)}</ul>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">Assumptions and AI suggestions</h2>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">{[...result.assumptions, ...result.ai_suggestions].map((item, index) => <li key={index}>{item}</li>)}</ul>
                <h3 className="mt-4 text-sm font-semibold text-amber-200">External research not performed</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-100">{result.missing_external_research.map((item, index) => <li key={index}>{item}</li>)}</ul>
              </div>
            </section>
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <h2 className="font-semibold">Publishing preparation checklist</h2>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-300">{result.publishing_preparation_checklist.map((item, index) => <li key={index}>{item}</li>)}</ul>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

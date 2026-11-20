"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Lightbulb } from "lucide-react";
import { BookSubNav } from "@/components/book-sub-nav";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";

type Provenance = "REAL_KDP_REPORT" | "SIMULATED_DEMO";
type ReportType = "ORDERS" | "KENP_READ" | "PRIOR_MONTH_ROYALTIES";

interface Recommendations {
  book_title: string;
  total_recommendations: number;
  recommendations: Array<{
    id: string;
    title: string;
    category: string;
    supporting_evidence: string;
    suggested_action: string;
    provenance: Provenance;
    disclaimer: string;
  }>;
  data_sources_evaluated: string[];
  demo_disclaimer?: string | null;
  disclaimer: string;
}

interface Book {
  id: string;
  title: string;
  status: string;
  print_format: string;
  trim_size: string;
}

export default function BusinessRecommendationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [provenance, setProvenance] = useState<Provenance>("REAL_KDP_REPORT");
  const [reportType, setReportType] = useState<ReportType>("ORDERS");
  const [result, setResult] = useState<Recommendations | null>(null);
  const [loading, setLoading] = useState(true);
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

  useEffect(() => {
    if (!isAuthenticated || !id) return;
    setLoading(true);
    setError(null);
    setResult(null);
    apiClient<Recommendations>(`/api/v1/books/${id}/business-recommendations?report_type=${reportType}&provenance=${provenance}`)
      .then(setResult)
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : "Could not load business recommendations.");
      })
      .finally(() => setLoading(false));
  }, [isAuthenticated, id, reportType, provenance]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      {book && <BookSubNav bookId={book.id} bookTitle={book.title} status={book.status} printFormat={book.print_format} trimSize={book.trim_size} />}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-amber-400">Evidence-based observations</p>
            <h1 className="text-3xl font-bold mt-1">Business recommendations</h1>
            <p className="mt-2 text-sm text-slate-400">Recommendations use only persisted book metadata and the selected provenance of uploaded reports.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              Report type
              <select value={reportType} onChange={(event) => setReportType(event.target.value as ReportType)} className="ml-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                <option value="ORDERS">Orders</option>
                <option value="KENP_READ">KENP Read</option>
                <option value="PRIOR_MONTH_ROYALTIES">Prior Month&apos;s Royalties</option>
              </select>
            </label>
            <label className="text-sm">
              Data provenance
              <select value={provenance} onChange={(event) => setProvenance(event.target.value as Provenance)} className="ml-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                <option value="REAL_KDP_REPORT">Real KDP report</option>
                <option value="SIMULATED_DEMO">Simulated demo</option>
              </select>
            </label>
          </div>
        </header>

        {provenance === "SIMULATED_DEMO" && (
          <p className="rounded-md border border-amber-500/40 bg-amber-950/30 p-3 text-sm font-bold text-amber-200">
            DEMO DATA — NOT REAL KDP EARNINGS
          </p>
        )}
        {error && <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-4 text-rose-200">{error}</p>}
        {loading ? <p className="text-slate-400">Loading recommendations…</p> : error ? null : !result || result.total_recommendations === 0 ? (
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
            <Lightbulb className="mx-auto h-8 w-8 text-slate-500" />
            <h2 className="mt-3 text-lg font-semibold">No evidence-based recommendations yet</h2>
            <p className="mt-1 text-sm text-slate-400">Import reports for this provenance to enable sales observations. No performance estimates are generated.</p>
            <button onClick={() => router.push(`/books/${id}/sales-import`)} className="mt-4 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950">Import reports</button>
          </section>
        ) : (
          <>
            <p className="text-xs text-slate-500">Sources: {result.data_sources_evaluated.join(" · ")}</p>
            <section className="space-y-4">
              {result.recommendations.map((item) => (
                <article key={item.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold">{item.title}</h2>
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{item.category}</span>
                    <span className="rounded-full bg-slate-800 px-2 py-1 text-[10px] text-slate-300">{item.provenance}</span>
                  </div>
                  <p className="mt-3 text-sm text-slate-300"><strong>Evidence:</strong> {item.supporting_evidence}</p>
                  <p className="mt-2 text-sm text-amber-100"><strong>Suggested action:</strong> {item.suggested_action}</p>
                  <p className="mt-3 text-xs text-slate-500">{item.disclaimer}</p>
                </article>
              ))}
            </section>
            <p className="text-xs text-slate-500">{result.disclaimer}</p>
          </>
        )}
      </main>
    </div>
  );
}

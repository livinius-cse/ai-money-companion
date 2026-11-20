"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { BarChart3, Upload } from "lucide-react";
import { BookSubNav } from "@/components/book-sub-nav";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";

type Provenance = "REAL_KDP_REPORT" | "SIMULATED_DEMO";
type ReportType = "ORDERS" | "KENP_READ" | "PRIOR_MONTH_ROYALTIES";

interface Analytics {
  report_type: ReportType;
  provenance: Provenance;
  is_demo: boolean;
  demo_disclaimer?: string | null;
  total_paid_units: number;
  total_free_units: number;
  total_kenp_read_pages: number;
  batch_count: number;
  transaction_count: number;
  royalty_totals: Array<{ currency: string; reported_royalties: number }>;
  marketplace_breakdown: Array<{
    marketplace: string;
    paid_units: number;
    free_units: number;
    kenp_read_pages: number;
    royalties_by_currency: Record<string, number>;
  }>;
  format_breakdown: Array<{
    format?: string | null;
    paid_units: number;
    free_units: number;
  }>;
  reporting_periods: string[];
  earliest_date?: string | null;
  latest_date?: string | null;
}

interface Book {
  id: string;
  title: string;
  status: string;
  print_format: string;
  trim_size: string;
}

const REPORT_LABELS: Record<ReportType, string> = {
  ORDERS: "Orders",
  KENP_READ: "KENP Read",
  PRIOR_MONTH_ROYALTIES: "Prior Month's Royalties",
};

export default function AnalyticsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [reportType, setReportType] = useState<ReportType>("ORDERS");
  const [provenance, setProvenance] = useState<Provenance>("REAL_KDP_REPORT");
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push("/login");
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated || !id) return;
    void apiClient<Book>(`/api/v1/books/${id}`)
      .then(setBook)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load book."));
  }, [isAuthenticated, id]);

  useEffect(() => {
    if (!isAuthenticated || !id) return;
    setLoading(true);
    setError(null);
    apiClient<Analytics>(
      `/api/v1/books/${id}/sales/analytics?report_type=${reportType}&provenance=${provenance}`
    )
      .then(setAnalytics)
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "Could not load imported sales analytics.")
      )
      .finally(() => setLoading(false));
  }, [isAuthenticated, id, reportType, provenance]);

  const hasData = !!analytics && analytics.transaction_count > 0;
  const orderTotals = [
    ["Paid units", analytics?.total_paid_units ?? 0],
    ["Free units", analytics?.total_free_units ?? 0],
    ["Imported rows", analytics?.transaction_count ?? 0],
  ] as const;
  const displayedTotals = reportType === "ORDERS"
    ? orderTotals
    : reportType === "KENP_READ"
      ? [["KENP pages read", analytics?.total_kenp_read_pages ?? 0], ["Imported rows", analytics?.transaction_count ?? 0]] as const
      : [["Imported rows", analytics?.transaction_count ?? 0]] as const;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      {book && <BookSubNav bookId={book.id} bookTitle={book.title} status={book.status} printFormat={book.print_format} trimSize={book.trim_size} />}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-amber-400">Persisted report data only</p>
            <h1 className="text-3xl font-bold mt-1">Sales analytics</h1>
            <p className="text-sm text-slate-400 mt-2">Historical report values only; no currency conversion, royalty estimates from orders, or future income projection.</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm">
              Report type
              <select value={reportType} onChange={(event) => setReportType(event.target.value as ReportType)} className="ml-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                {Object.entries(REPORT_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </label>
            <label className="text-sm">
              Provenance
              <select value={provenance} onChange={(event) => setProvenance(event.target.value as Provenance)} className="ml-2 rounded-md border border-slate-700 bg-slate-900 px-3 py-2">
                <option value="REAL_KDP_REPORT">Real KDP report</option>
                <option value="SIMULATED_DEMO">Simulated demo</option>
              </select>
            </label>
          </div>
        </header>

        {analytics?.is_demo && (
          <p className="rounded-md border border-amber-500/40 bg-amber-950/30 p-3 text-sm font-bold text-amber-200">
            DEMO DATA — NOT REAL KDP EARNINGS
          </p>
        )}
        {error && <p role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-4 text-rose-200">{error}</p>}
        {loading ? <p className="text-slate-400">Loading analytics…</p> : error ? null : !hasData ? (
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
            <BarChart3 className="mx-auto h-8 w-8 text-slate-500" />
            <h2 className="mt-3 text-lg font-semibold">No {REPORT_LABELS[reportType]} report data</h2>
            <p className="mt-1 text-sm text-slate-400">Import a report to see values for this report type.</p>
            <button onClick={() => router.push(`/books/${id}/sales-import`)} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950">
              <Upload className="h-4 w-4" /> Import a report
            </button>
          </section>
        ) : analytics && (
          <>
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {displayedTotals.map(([label, value]) => (
                <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <p className="text-xs text-slate-400">{label}</p>
                  <p className="mt-2 text-2xl font-bold">{value.toLocaleString()}</p>
                </div>
              ))}
            </section>
            {reportType === "PRIOR_MONTH_ROYALTIES" && (
              <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">Reported royalties · kept separate by currency</h2>
                <ul className="mt-3 divide-y divide-slate-800">
                  {analytics.royalty_totals.map((item) => (
                    <li key={item.currency} className="flex justify-between py-3 text-sm">
                      <span>{item.currency}</span>
                      <span>{item.reported_royalties.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <section className="grid gap-5 lg:grid-cols-2">
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                <h2 className="font-semibold">Marketplace results</h2>
                <ul className="mt-3 divide-y divide-slate-800">
                  {analytics.marketplace_breakdown.map((item) => (
                    <li key={item.marketplace} className="py-3 text-sm">
                      <div className="flex justify-between gap-3">
                        <span>{item.marketplace}</span>
                        <span className="text-right">
                          {reportType === "ORDERS"
                            ? `${item.paid_units.toLocaleString()} paid · ${item.free_units.toLocaleString()} free`
                            : reportType === "KENP_READ"
                              ? `${item.kenp_read_pages.toLocaleString()} KENP pages`
                              : Object.entries(item.royalties_by_currency).map(([currency, amount]) => `${currency} ${amount.toFixed(2)}`).join(" · ")}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
              {reportType === "ORDERS" && (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
                  <h2 className="font-semibold">Format breakdown</h2>
                  <ul className="mt-3 divide-y divide-slate-800">
                    {analytics.format_breakdown.map((item, index) => (
                      <li key={`${item.format}-${index}`} className="flex justify-between py-3 text-sm">
                        <span>{item.format || "Format not mapped"}</span>
                        <span>{item.paid_units.toLocaleString()} paid · {item.free_units.toLocaleString()} free</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 lg:col-span-2">
                <h2 className="font-semibold">Reporting periods</h2>
                {analytics.reporting_periods.length ? (
                  <p className="mt-3 text-sm text-slate-300">{analytics.reporting_periods.join(" · ")}</p>
                ) : <p className="mt-3 text-sm text-slate-400">No reporting periods recorded.</p>}
                <p className="mt-2 text-xs text-slate-500">
                  {analytics.batch_count} valid import batch(es) · {analytics.earliest_date || "—"} to {analytics.latest_date || "—"}
                </p>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Download, Package, RefreshCw, ShieldCheck } from "lucide-react";
import { BookSubNav } from "@/components/book-sub-nav";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";

interface ExportPackage {
  id: string;
  export_version: number;
  filename: string;
  file_size_bytes: number;
  sha256_hash: string;
  manifest_data: Record<string, unknown>;
  created_at: string;
}

interface ExportEligibility {
  is_eligible: boolean;
  blocking_reasons: string[];
  active_approval_id?: string | null;
}

interface Book {
  id: string;
  title: string;
  status: string;
  print_format: string;
  trim_size: string;
}

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [eligibility, setEligibility] = useState<ExportEligibility | null>(null);
  const [packages, setPackages] = useState<ExportPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push("/login");
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && id) void loadData();
  }, [isAuthenticated, id]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [bookData, eligibilityData, historyData] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${id}`),
        apiClient<ExportEligibility>(`/api/v1/books/${id}/exports/eligibility`),
        apiClient<{ items: ExportPackage[] }>(`/api/v1/books/${id}/exports`),
      ]);
      setBook(bookData);
      setEligibility(eligibilityData);
      setPackages(historyData.items || []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load export information.");
    } finally {
      setLoading(false);
    }
  }

  async function generatePackage() {
    setGenerating(true);
    setError(null);
    try {
      await apiClient<ExportPackage>(`/api/v1/books/${id}/exports`, { method: "POST" });
      await loadData();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Package generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      {book && (
        <BookSubNav
          bookId={book.id}
          bookTitle={book.title}
          status={book.status}
          printFormat={book.print_format}
          trimSize={book.trim_size}
        />
      )}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header>
          <p className="text-xs uppercase tracking-wider text-amber-400">Milestone 6 · Manual handoff</p>
          <h1 className="text-3xl font-bold mt-1">KDP package export</h1>
          <p className="text-sm text-slate-400 mt-2">
            Build a private ZIP from the currently approved edition. This does not upload or publish to Amazon KDP.
          </p>
        </header>

        {error && <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-4 text-rose-200">{error}</div>}

        {eligibility && (
          <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
            <div className="flex items-center gap-2 font-semibold">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              {eligibility.is_eligible ? "Approval and source hashes verified" : "Export is blocked"}
            </div>
            {eligibility.blocking_reasons.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-200">
                {eligibility.blocking_reasons.map((reason, index) => <li key={index}>{reason}</li>)}
              </ul>
            )}
            <button
              onClick={generatePackage}
              disabled={!eligibility.is_eligible || generating}
              className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Package className="h-4 w-4" />
              {generating ? "Creating ZIP…" : "Generate KDP ZIP"}
            </button>
          </section>
        )}

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Export history</h2>
            <button onClick={() => void loadData()} className="text-sm text-slate-300 hover:text-white" aria-label="Refresh exports">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          {loading ? (
            <p className="mt-4 text-sm text-slate-400">Loading exports…</p>
          ) : packages.length === 0 ? (
            <p className="mt-4 text-sm text-slate-400">No export packages have been generated.</p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-800">
              {packages.map((item) => (
                <li key={item.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium">{item.filename}</p>
                    <p className="text-xs text-slate-400">
                      Version {item.export_version} · {new Date(item.created_at).toLocaleString()} · {item.file_size_bytes.toLocaleString()} bytes
                    </p>
                    <p className="mt-1 break-all font-mono text-xs text-slate-500">SHA-256 {item.sha256_hash}</p>
                  </div>
                  <a
                    className="inline-flex items-center gap-2 self-start rounded-md border border-slate-700 px-3 py-2 text-sm hover:bg-slate-800"
                    href={`/api/v1/books/${id}/exports/${item.id}/download`}
                  >
                    <Download className="h-4 w-4" /> Download
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

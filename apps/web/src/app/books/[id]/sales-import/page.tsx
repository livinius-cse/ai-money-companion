"use client";

import React, { ChangeEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { FileUp, RefreshCw } from "lucide-react";
import { BookSubNav } from "@/components/book-sub-nav";
import { Navbar } from "@/components/navbar";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";

type Provenance = "REAL_KDP_REPORT" | "SIMULATED_DEMO";
type ReportType = "ORDERS" | "KENP_READ" | "PRIOR_MONTH_ROYALTIES";

interface ImportField {
  key: string;
  label: string;
  required: boolean;
}

interface ImportPreview {
  source_sha256: string;
  report_type: ReportType;
  provenance: Provenance;
  source_headers: string[];
  fields: ImportField[];
  column_mapping: Record<string, string>;
  source_preview: Array<Record<string, string | null>>;
  mapped_preview: Array<Record<string, unknown>>;
  row_count: number;
  validation_errors: string[];
  can_import: boolean;
}

interface ImportBatch {
  id: string;
  original_filename: string;
  report_type: string;
  source_sha256: string;
  reporting_period?: string | null;
  marketplace?: string | null;
  currency?: string | null;
  row_count: number;
  provenance: Provenance;
  status: string;
  validation_result?: { errors?: string[] } | null;
  created_at: string;
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

function getErrorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}

export default function SalesImportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [book, setBook] = useState<Book | null>(null);
  const [reportType, setReportType] = useState<ReportType>("ORDERS");
  const [provenance, setProvenance] = useState<Provenance>("REAL_KDP_REPORT");
  const [file, setFile] = useState<File | null>(null);
  const [imports, setImports] = useState<ImportBatch[]>([]);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [previewing, setPreviewing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push("/login");
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated || !id) return;
    void apiClient<Book>(`/api/v1/books/${id}`)
      .then(setBook)
      .catch((reason) => setError(getErrorMessage(reason, "Could not load book.")));
  }, [isAuthenticated, id]);

  useEffect(() => {
    if (isAuthenticated && id) void loadImports();
  }, [isAuthenticated, id, provenance, reportType]);

  function resetPreview() {
    setPreview(null);
    setMapping({});
    setMessage(null);
    setError(null);
  }

  async function loadImports() {
    setLoading(true);
    try {
      const result = await apiClient<{ items: ImportBatch[] }>(
        `/api/v1/books/${id}/sales/imports?report_type=${reportType}&provenance=${provenance}`
      );
      setImports(result.items);
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not load import history."));
    } finally {
      setLoading(false);
    }
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] || null);
    resetPreview();
  }

  async function requestPreview(columnMapping: Record<string, string>) {
    if (!file) return;
    setPreviewing(true);
    setError(null);
    setMessage(null);
    const form = new FormData();
    form.set("report", file);
    form.set("report_type", reportType);
    form.set("provenance", provenance);
    form.set("column_mapping_json", JSON.stringify(columnMapping));
    try {
      const response = await apiClient<ImportPreview>(
        `/api/v1/books/${id}/sales/import/preview`,
        { method: "POST", body: form }
      );
      setPreview(response);
      setMapping(response.column_mapping);
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not preview this report."));
    } finally {
      setPreviewing(false);
    }
  }

  async function previewMappedRows() {
    await requestPreview(mapping);
  }

  async function confirmImport() {
    if (!file || !preview?.can_import) return;
    setConfirming(true);
    setError(null);
    setMessage(null);
    const form = new FormData();
    form.set("report", file);
    form.set("report_type", reportType);
    form.set("provenance", provenance);
    form.set("column_mapping_json", JSON.stringify(mapping));
    form.set("expected_source_sha256", preview.source_sha256);
    try {
      const result = await apiClient<ImportBatch>(
        `/api/v1/books/${id}/sales/import/confirm`,
        { method: "POST", body: form }
      );
      setMessage(
        result.status === "VALID"
          ? `Imported ${result.row_count} ${REPORT_LABELS[reportType]} row(s).`
          : `No rows were imported: ${result.validation_result?.errors?.join("; ") || "The report failed validation."}`
      );
      setFile(null);
      setPreview(null);
      setMapping({});
      await loadImports();
    } catch (reason) {
      setError(getErrorMessage(reason, "Could not confirm this report import."));
    } finally {
      setConfirming(false);
    }
  }

  function updateMapping(field: string, header: string) {
    const updated = { ...mapping };
    if (header) updated[field] = header;
    else delete updated[field];
    setMapping(updated);
    setPreview((current) =>
      current ? { ...current, column_mapping: updated, mapped_preview: [], can_import: false, validation_errors: [] } : current
    );
    setMessage(null);
    setError(null);
  }

  const requiredFieldsMapped = !!preview?.fields
    .filter((field) => field.required)
    .every((field) => !!mapping[field.key]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />
      {book && <BookSubNav bookId={book.id} bookTitle={book.title} status={book.status} printFormat={book.print_format} trimSize={book.trim_size} />}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header>
          <p className="text-xs uppercase tracking-wider text-amber-400">Milestone 6 · User-uploaded reports</p>
          <h1 className="text-3xl font-bold mt-1">Sales report imports</h1>
          <p className="text-sm text-slate-400 mt-2">
            Upload an Orders, KENP Read, or Prior Month&apos;s Royalties report. This application does not connect to your Amazon account or scrape KDP.
          </p>
        </header>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <p className="rounded-md border border-blue-500/30 bg-blue-950/20 p-3 text-sm text-blue-100">
            Official KDP field semantics are documented. Exact downloaded-file header compatibility must be confirmed against actual user-exported files.
          </p>
          <p className="text-xs text-slate-400">
            Official references:{" "}
            <a className="underline" href="https://kdp.amazon.com/en_US/help/topic/GVTTXHKHVPAPBEDQ" target="_blank" rel="noreferrer">KDP Reports</a>
            {" · "}
            <a className="underline" href="https://kdp.amazon.com/en_US/help/topic/GNT7B2H74F5NJZW3" target="_blank" rel="noreferrer">Orders</a>
            {" · "}
            <a className="underline" href="https://kdp.amazon.com/en_US/help/topic/GNRKU6NDYY2AGTTK" target="_blank" rel="noreferrer">KENP Read</a>
            {" · "}
            <a className="underline" href="https://kdp.amazon.com/en_US/help/topic/G200641190" target="_blank" rel="noreferrer">Prior Month&apos;s Royalties</a>
          </p>
          <label className="block text-sm font-medium">
            Report type
            <select
              value={reportType}
              onChange={(event) => {
                setReportType(event.target.value as ReportType);
                resetPreview();
              }}
              className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            >
              {Object.entries(REPORT_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Report provenance
            <select
              value={provenance}
              onChange={(event) => {
                setProvenance(event.target.value as Provenance);
                resetPreview();
              }}
              className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
            >
              <option value="REAL_KDP_REPORT">REAL_KDP_REPORT</option>
              <option value="SIMULATED_DEMO">SIMULATED_DEMO</option>
            </select>
          </label>
          {provenance === "SIMULATED_DEMO" && (
            <p className="rounded-md border border-amber-500/40 bg-amber-950/30 p-3 text-sm font-semibold text-amber-200">
              DEMO DATA — NOT REAL KDP EARNINGS
            </p>
          )}
          <label className="block text-sm">
            Upload report file
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={chooseFile}
              className="mt-2 block w-full text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-700 file:px-3 file:py-2 file:text-white"
            />
          </label>
          {file && <p className="text-xs text-slate-400">{file.name} · {file.size.toLocaleString()} bytes</p>}
          {file && !preview && (
            <button
              onClick={() => void requestPreview({})}
              disabled={previewing}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-40"
            >
              <FileUp className="h-4 w-4" /> {previewing ? "Reading headers…" : "Detect report headers"}
            </button>
          )}
          {preview && (
            <div className="space-y-4 border-t border-slate-800 pt-4">
              <div>
                <h2 className="font-semibold">Detected source headers</h2>
                <p className="mt-1 break-all font-mono text-xs text-slate-400">SHA-256 {preview.source_sha256}</p>
                <p className="text-xs text-slate-400">{preview.row_count} source row(s) detected.</p>
              </div>
              <p className="text-sm text-amber-100">Map each canonical field explicitly. No column names are guessed or auto-mapped.</p>
              <div className="grid gap-3 md:grid-cols-2">
                {preview.fields.map((field) => (
                  <label key={field.key} className="block text-sm">
                    {field.label} {field.required ? <span className="text-rose-300">(required)</span> : <span className="text-slate-500">(optional)</span>}
                    <select
                      value={mapping[field.key] || ""}
                      onChange={(event) => updateMapping(field.key, event.target.value)}
                      className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
                    >
                      <option value="">Do not map</option>
                      {preview.source_headers.map((header, index) => (
                        <option key={`${header}-${index}`} value={header}>{header || "(blank header)"}</option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <button
                onClick={() => void previewMappedRows()}
                disabled={!requiredFieldsMapped || previewing}
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold disabled:opacity-40"
              >
                {previewing ? "Validating mapped rows…" : "Preview mapped records"}
              </button>
              {preview.source_preview.length > 0 && (
                <div className="overflow-x-auto">
                  <h3 className="mb-2 text-sm font-semibold">Raw file sample (source names retained)</h3>
                  <table className="min-w-full text-left text-xs">
                    <thead><tr>{preview.source_headers.map((header, index) => <th key={`${header}-${index}`} className="px-2 py-2 text-slate-400">{header}</th>)}</tr></thead>
                    <tbody>{preview.source_preview.map((row, rowIndex) => (
                      <tr key={rowIndex} className="border-t border-slate-800">
                        {preview.source_headers.map((header, index) => <td key={`${header}-${index}`} className="max-w-56 truncate px-2 py-2">{row[header] ?? "—"}</td>)}
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
              {preview.validation_errors.length > 0 && (
                <div role="alert" className="rounded-lg border border-rose-500/40 bg-rose-950/30 p-3 text-sm text-rose-200">
                  <p className="font-semibold">Validation issues</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5">{preview.validation_errors.map((item, index) => <li key={index}>{item}</li>)}</ul>
                </div>
              )}
              {preview.mapped_preview.length > 0 && (
                <div className="overflow-x-auto">
                  <h3 className="mb-2 text-sm font-semibold">Mapped record preview</h3>
                  <pre className="max-h-72 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-300">{JSON.stringify(preview.mapped_preview, null, 2)}</pre>
                </div>
              )}
              {preview.can_import && (
                <button
                  onClick={() => void confirmImport()}
                  disabled={confirming}
                  className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-bold text-slate-950 disabled:opacity-40"
                >
                  {confirming ? "Saving confirmed import…" : `Confirm import of ${preview.row_count} rows`}
                </button>
              )}
            </div>
          )}
          {message && <p role="status" className="text-sm text-emerald-300">{message}</p>}
          {error && <p role="alert" className="text-sm text-rose-300">{error}</p>}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Import history · {REPORT_LABELS[reportType]} · {provenance}</h2>
            <button onClick={() => void loadImports()} aria-label="Refresh import history" className="text-slate-300 hover:text-white">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          {loading ? <p className="mt-4 text-sm text-slate-400">Loading imports…</p> : imports.length === 0 ? (
            <p className="mt-4 text-sm text-slate-400">No reports imported for this report type and provenance.</p>
          ) : (
            <ul className="mt-4 divide-y divide-slate-800">
              {imports.map((batch) => (
                <li key={batch.id} className="py-4">
                  <p className="font-medium">{batch.original_filename} <span className={batch.status === "VALID" ? "text-emerald-300" : "text-rose-300"}>· {batch.status}</span></p>
                  <p className="text-xs text-slate-400">
                    {batch.reporting_period || "Multiple periods"} · {batch.marketplace || "Multiple marketplaces"} · {batch.currency || "No royalty currency"} · {batch.row_count} rows · {new Date(batch.created_at).toLocaleString()}
                  </p>
                  <p className="mt-1 break-all font-mono text-[10px] text-slate-500">SHA-256 {batch.source_sha256}</p>
                  {!!batch.validation_result?.errors?.length && (
                    <p className="mt-1 text-sm text-rose-300">{batch.validation_result.errors.join("; ")}</p>
                  )}
                  {batch.provenance === "SIMULATED_DEMO" && (
                    <p className="mt-2 text-xs font-semibold text-amber-200">DEMO DATA — NOT REAL KDP EARNINGS</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

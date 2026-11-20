"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  CheckCircle2,
  AlertOctagon,
  AlertTriangle,
  Info,
  ShieldCheck,
  ShieldAlert,
  Hash,
  FileCheck,
  RefreshCw,
  Lock,
  History,
  ArrowRight,
  BookOpen,
  Palette,
  FileText,
} from "lucide-react";

interface QAFinding {
  rule_id: string;
  category: "MANUSCRIPT" | "INTERIOR" | "COVER" | "METADATA";
  severity: "BLOCKING" | "WARNING" | "INFO";
  explanation: string;
  relevant_field: string;
  observed_value: any;
  remediation: string;
}

interface CryptographicHashes {
  manuscript_hash?: string;
  metadata_hash?: string;
  interior_hash?: string;
  cover_hash?: string;
  composite_hash?: string;
  hash_scheme_version: string;
}

interface DocumentVersionInfo {
  interior_id?: string;
  interior_version?: number;
  interior_page_count?: number;
  interior_file_size?: number;
  cover_id?: string;
  cover_version?: number;
  cover_file_size?: number;
}

interface PreFlightQAReport {
  report_id: string;
  book_id: string;
  book_title: string;
  timestamp: string;
  is_ready_for_approval: boolean;
  blocking_count: number;
  warning_count: number;
  info_count: number;
  findings: QAFinding[];
  hashes: CryptographicHashes;
  document_versions: DocumentVersionInfo;
  ai_disclosure_attested: boolean;
  readability_summary?: any;
}

interface ApprovalSnapshot {
  id: string;
  snapshot_version: number;
  status: string;
  manuscript_hash: string;
  metadata_hash: string;
  interior_hash: string;
  cover_hash: string;
  composite_hash: string;
  hash_scheme_version: string;
  approval_attestation: string;
  created_at: string;
  invalidated_at?: string;
  invalidation_reason?: string;
}

interface ApprovalVerificationResult {
  is_valid: boolean;
  active_snapshot?: ApprovalSnapshot;
  hash_match: boolean;
  current_hashes: Record<string, string>;
  divergences: string[];
  remediation?: string;
}

export default function PreFlightQAPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<any>(null);
  const [report, setReport] = useState<PreFlightQAReport | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<ApprovalVerificationResult | null>(null);
  const [history, setHistory] = useState<ApprovalSnapshot[]>([]);

  const [loading, setLoading] = useState(true);
  const [runningQA, setRunningQA] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const [attestationText, setAttestationText] = useState(
    "I confirm that I have reviewed the complete pre-flight QA report, all physical and metadata specifications comply with Amazon KDP requirements, and this publishing edition is approved."
  );
  const [attestationConfirmed, setAttestationConfirmed] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && bookId) {
      loadAllData();
    }
  }, [isAuthenticated, bookId]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bookData, reportData, statusData, historyData] = await Promise.all([
        apiClient<any>(`/api/v1/books/${bookId}`),
        apiClient<PreFlightQAReport>(`/api/v1/books/${bookId}/preflight/report`),
        apiClient<ApprovalVerificationResult>(`/api/v1/books/${bookId}/preflight/approval`),
        apiClient<{ items: ApprovalSnapshot[]; total: number }>(`/api/v1/books/${bookId}/preflight/approval/history`),
      ]);
      setBook(bookData);
      setReport(reportData);
      setApprovalStatus(statusData);
      setHistory(historyData.items || []);
    } catch (err: any) {
      console.error("Failed to load pre-flight data:", err);
      setError(err.message || "Failed to load pre-flight verification data.");
    } finally {
      setLoading(false);
    }
  };

  const handleRunFreshQA = async () => {
    try {
      setRunningQA(true);
      setError(null);
      setSuccessMsg(null);
      const updatedReport = await apiClient<PreFlightQAReport>(`/api/v1/books/${bookId}/preflight/run`, {
        method: "POST",
      });
      setReport(updatedReport);
      const statusData = await apiClient<ApprovalVerificationResult>(`/api/v1/books/${bookId}/preflight/approval`);
      setApprovalStatus(statusData);
      setSuccessMsg("Pre-flight QA re-audit completed successfully.");
    } catch (err: any) {
      setError(err.message || "Failed to run QA inspection.");
    } finally {
      setRunningQA(false);
    }
  };

  const handleApprove = async () => {
    if (!attestationConfirmed) {
      setError("Please confirm the explicit approval attestation checkbox before signing off.");
      return;
    }
    try {
      setApproving(true);
      setError(null);
      setSuccessMsg(null);
      await apiClient(`/api/v1/books/${bookId}/preflight/approve`, {
        method: "POST",
        body: JSON.stringify({ attestation: attestationText }),
      });
      setSuccessMsg("Publication edition successfully approved! Cryptographic manifest snapshot frozen.");
      await loadAllData();
    } catch (err: any) {
      setError(err.message || "Approval sign-off failed.");
    } finally {
      setApproving(false);
    }
  };

  if (authLoading || loading || !book || !report) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  const blockingFindings = report.findings.filter((f) => f.severity === "BLOCKING");
  const warningFindings = report.findings.filter((f) => f.severity === "WARNING");
  const infoFindings = report.findings.filter((f) => f.severity === "INFO");

  const isApproved = approvalStatus?.is_valid && approvalStatus.active_snapshot;

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
        {/* Top Header & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-500">
                Milestone 5 • Quality Assurance Gate
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mt-1">
              Pre-Flight QA & Cryptographic Approval
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              Deterministic verification across manuscript, interior PDF, cover jacket, and KDP metadata.
              Amazon KDP export packages cannot be generated without an active cryptographic approval snapshot.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunFreshQA}
              disabled={runningQA}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${runningQA ? "animate-spin" : ""}`} />
              <span>{runningQA ? "Auditing..." : "Re-Run QA Audit"}</span>
            </button>
            {isApproved && (
              <button
                onClick={() => router.push(`/books/${book.id}/export`)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/20 transition"
              >
                <span>Proceed to Export</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Feedback alerts */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
            <AlertOctagon className="w-5 h-5 flex-shrink-0 text-rose-400 mt-0.5" />
            <div>
              <div className="font-semibold">Verification Alert</div>
              <div>{typeof error === "string" ? error : JSON.stringify(error)}</div>
            </div>
          </div>
        )}
        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400 mt-0.5" />
            <div>
              <div className="font-semibold">Action Succeeded</div>
              <div>{successMsg}</div>
            </div>
          </div>
        )}

        {/* Status Banners: Active Approval vs Invalidation */}
        {isApproved ? (
          <div className="p-6 rounded-2xl bg-emerald-950/40 border border-emerald-500/40 shadow-xl shadow-emerald-950/20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center flex-shrink-0 text-emerald-400">
                  <ShieldCheck className="w-7 h-7" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      Approval Active • v{approvalStatus.active_snapshot?.snapshot_version}
                    </span>
                    <span className="text-xs text-slate-400">
                      Signed {new Date(approvalStatus.active_snapshot?.created_at || "").toLocaleString()}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">Cryptographic Approval Gate Unlocked</h3>
                  <p className="text-slate-300 text-xs mt-1 italic">
                    "{approvalStatus.active_snapshot?.approval_attestation}"
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-slate-400 font-mono">Composite Hash:</div>
                <div className="text-xs font-mono text-emerald-400 font-semibold truncate max-w-xs sm:max-w-sm">
                  {approvalStatus.active_snapshot?.composite_hash}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-6 rounded-2xl bg-amber-950/20 border border-amber-500/30">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 text-amber-400">
                <ShieldAlert className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Pending Human Sign-Off & Verification</h3>
                <p className="text-slate-400 text-xs mt-1">
                  {report.blocking_count > 0
                    ? `Resolve all ${report.blocking_count} blocking QA issue(s) before this book can be approved.`
                    : "All blocking QA checks have passed. Review the findings and sign off below to lock the publishing edition."}
                </p>
                {approvalStatus?.divergences && approvalStatus.divergences.length > 0 && (
                  <div className="mt-2 text-xs text-amber-300 font-mono">
                    Prior approval invalidated: {approvalStatus.divergences.join("; ")}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Readiness Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Readiness Gate</div>
            <div className="mt-2 flex items-center gap-2">
              {report.is_ready_for_approval ? (
                <>
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-lg font-bold text-emerald-400">READY</span>
                </>
              ) : (
                <>
                  <AlertOctagon className="w-5 h-5 text-rose-400" />
                  <span className="text-lg font-bold text-rose-400">BLOCKED</span>
                </>
              )}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              {report.blocking_count === 0 ? "0 blocking checks" : `${report.blocking_count} blocking error(s)`}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Blocking Issues</div>
            <div className="mt-2 text-2xl font-bold text-rose-400">{report.blocking_count}</div>
            <div className="text-[11px] text-slate-500 mt-1">Must be resolved for approval</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">Advisory Warnings</div>
            <div className="mt-2 text-2xl font-bold text-amber-400">{report.warning_count}</div>
            <div className="text-[11px] text-slate-500 mt-1">KDP recommended optimizations</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-xs text-slate-400 font-medium">AI Disclosure Status</div>
            <div className="mt-2 flex items-center gap-2">
              {report.ai_disclosure_attested ? (
                <>
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-sm font-bold text-emerald-400">CONFIRMED</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-5 h-5 text-amber-400" />
                  <span className="text-sm font-bold text-amber-400">REQUIRED</span>
                </>
              )}
            </div>
            <div className="text-[11px] text-slate-500 mt-1">Amazon KDP compliance mandate</div>
          </div>
        </div>

        {/* 5-Way Cryptographic Hashes Panel */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Hash className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Five-Way Cryptographic Verification
              </h2>
            </div>
            <span className="text-xs font-mono text-slate-400">
              Scheme: <span className="text-amber-400">{report.hashes.hash_scheme_version}</span>
            </span>
          </div>

          <p className="text-xs text-slate-400">
            Every component is hashed deterministically using canonical JSON (Unicode NFC normalized, sorted keys, compact serialization)
            and actual stored PDF bytes.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-400 text-[11px] flex items-center justify-between mb-1">
                <span>1. MANUSCRIPT & APPROVED ASSETS</span>
                <span className="text-emerald-400">SHA-256</span>
              </div>
              <div className="text-slate-200 truncate">{report.hashes.manuscript_hash || "Missing content"}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-400 text-[11px] flex items-center justify-between mb-1">
                <span>2. KDP METADATA & CONFIG</span>
                <span className="text-emerald-400">SHA-256</span>
              </div>
              <div className="text-slate-200 truncate">{report.hashes.metadata_hash || "Missing metadata"}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-400 text-[11px] flex items-center justify-between mb-1">
                <span>3. INTERIOR PDF STORED BYTES</span>
                <span className="text-emerald-400">
                  {report.document_versions.interior_version ? `v${report.document_versions.interior_version}` : "Missing"}
                </span>
              </div>
              <div className="text-slate-200 truncate">{report.hashes.interior_hash || "Not compiled yet"}</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-400 text-[11px] flex items-center justify-between mb-1">
                <span>4. COVER PDF STORED BYTES</span>
                <span className="text-emerald-400">
                  {report.document_versions.cover_version ? `v${report.document_versions.cover_version}` : "Missing"}
                </span>
              </div>
              <div className="text-slate-200 truncate">{report.hashes.cover_hash || "Not compiled yet"}</div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 font-mono text-xs">
            <div className="text-amber-400 text-[11px] font-bold uppercase tracking-wider mb-1">
              5. COMPOSITE MANIFEST HASH (LOCK KEY)
            </div>
            <div className="text-white text-sm font-semibold truncate">
              {report.hashes.composite_hash || "Cannot compute until all 4 components exist"}
            </div>
          </div>
        </div>

        {/* QA Audit Findings Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FileCheck className="w-5 h-5 text-amber-400" />
              <span>Inspection Findings ({report.findings.length})</span>
            </h2>
          </div>

          {report.findings.length === 0 ? (
            <div className="p-8 text-center rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 text-sm">
              Zero findings recorded. All publishing checks passed.
            </div>
          ) : (
            <div className="space-y-3">
              {report.findings.map((f, idx) => {
                const isBlocking = f.severity === "BLOCKING";
                const isWarning = f.severity === "WARNING";

                const borderCls = isBlocking
                  ? "border-rose-500/30 bg-rose-950/10"
                  : isWarning
                  ? "border-amber-500/30 bg-amber-950/10"
                  : "border-slate-800 bg-slate-900/50";

                const badgeCls = isBlocking
                  ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                  : isWarning
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
                  : "bg-slate-800 text-slate-300 border-slate-700";

                const Icon = isBlocking ? AlertOctagon : isWarning ? AlertTriangle : Info;
                const iconColor = isBlocking ? "text-rose-400" : isWarning ? "text-amber-400" : "text-sky-400";

                return (
                  <div key={`${f.rule_id}-${idx}`} className={`p-4 rounded-xl border ${borderCls} space-y-2`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${iconColor}`} />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${badgeCls}`}>
                              {f.severity}
                            </span>
                            <span className="text-xs font-mono text-slate-400">[{f.rule_id}]</span>
                            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                              {f.category}
                            </span>
                          </div>
                          <div className="text-sm font-semibold text-white mt-1">{f.explanation}</div>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">{f.relevant_field}</span>
                    </div>

                    <div className="pl-7 text-xs space-y-1">
                      {f.observed_value !== null && f.observed_value !== undefined && (
                        <div className="text-slate-400 font-mono text-[11px]">
                          Observed: <span className="text-slate-300">{JSON.stringify(f.observed_value)}</span>
                        </div>
                      )}
                      <div className="text-slate-300 text-xs flex items-center gap-1.5">
                        <span className="text-amber-400 font-semibold">Remediation:</span>
                        <span>{f.remediation}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Human Approval Sign-Off Gate Card */}
        <div className="p-6 rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-slate-800 space-y-4">
          <div className="flex items-center gap-2 text-amber-400">
            <Lock className="w-5 h-5" />
            <h2 className="text-base font-bold text-white">Explicit Owner Sign-Off Gate</h2>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            By signing off, you attest that all physical dimensions, page counts, gutter margins, and cover geometries
            have been inspected and accepted. This action freezes an immutable approval snapshot with all 5 cryptographic hashes.
          </p>

          <div className="space-y-3">
            <label className="text-xs font-semibold text-slate-300 block">Author Sign-Off Attestation:</label>
            <textarea
              rows={3}
              value={attestationText}
              onChange={(e) => setAttestationText(e.target.value)}
              className="w-full text-xs font-mono p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-amber-500"
            />

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={attestationConfirmed}
                onChange={(e) => setAttestationConfirmed(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-amber-500 focus:ring-amber-500"
              />
              <span className="text-xs text-slate-300">
                I have inspected the verified PDF files and confirm publication readiness under Amazon KDP rules.
              </span>
            </label>
          </div>

          <div className="pt-2 flex items-center gap-4">
            <button
              onClick={handleApprove}
              disabled={approving || !attestationConfirmed || !report.is_ready_for_approval}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{approving ? "Signing & Hashing..." : "Sign Off & Approve Publication"}</span>
            </button>
            {!report.is_ready_for_approval && (
              <span className="text-xs text-rose-400">
                Cannot sign off: {report.blocking_count} blocking issue(s) remaining.
              </span>
            )}
          </div>
        </div>

        {/* Approval History Audit Trail */}
        {history.length > 0 && (
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Approval History & Invalidation Trail ({history.length})
              </h2>
            </div>

            <div className="space-y-2 text-xs">
              {history.map((snap) => (
                <div
                  key={snap.id}
                  className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                        snap.status === "ACTIVE"
                          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                          : snap.status === "INVALIDATED"
                          ? "bg-rose-500/20 text-rose-300 border-rose-500/30"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                    >
                      {snap.status}
                    </span>
                    <span className="font-semibold text-white">Snapshot v{snap.snapshot_version}</span>
                    <span className="text-slate-500">({new Date(snap.created_at).toLocaleString()})</span>
                  </div>

                  <div className="text-slate-400 text-[11px] truncate max-w-md">
                    {snap.invalidation_reason ? (
                      <span className="text-rose-400 font-mono">Reason: {snap.invalidation_reason}</span>
                    ) : (
                      <span className="text-slate-400 font-mono">Composite: {snap.composite_hash.slice(0, 16)}...</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

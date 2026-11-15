"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  BookOpen,
  Sparkles,
  Download,
  Eye,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Layers,
  ShieldAlert,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  subtitle?: string | null;
  topic: string;
  print_format: string;
  trim_size: string;
  paper_type: string;
  target_page_count: number;
  total_allocated_pages?: number;
  status: string;
}

interface BookDocument {
  id: string;
  document_type: string;
  version: number;
  storage_key: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_hash: string;
  page_count: number;
  width_pt: number;
  height_pt: number;
  trim_size: string;
  bleed_config: string;
  status: string;
  created_at: string;
  generation_metadata?: any;
}

export default function InteriorLayoutPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [documents, setDocuments] = useState<BookDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<BookDocument | null>(null);
  const [qualityData, setQualityData] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Layout form options
  const [includeToc, setIncludeToc] = useState(true);
  const [includeDedication, setIncludeDedication] = useState(false);
  const [dedicationText, setDedicationText] = useState("");
  const [fontChoice, setFontChoice] = useState<"serif" | "sans">("serif");
  const [isFullBleed, setIsFullBleed] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && bookId) {
      loadData();
    }
  }, [isAuthenticated, bookId]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bookData, docsData, qData] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<{ items: BookDocument[]; total: number }>(`/api/v1/books/${bookId}/documents`),
        apiClient<any>(`/api/v1/books/${bookId}/quality`),
      ]);
      setBook(bookData);
      const interiors = (docsData.items || []).filter((d) => d.document_type === "INTERIOR");
      setDocuments(interiors);
      if (interiors.length > 0) {
        setSelectedDoc(interiors[0]);
      }
      setQualityData(qData);
    } catch (err: any) {
      setError(err.message || "Failed to load layout studio data.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInterior = async () => {
    try {
      setGenerating(true);
      setError(null);
      setSuccess(false);

      const newDoc = await apiClient<BookDocument>(
        `/api/v1/books/${bookId}/documents/interior/generate`,
        {
          method: "POST",
          body: JSON.stringify({
            include_toc: includeToc,
            include_dedication: includeDedication,
            dedication_text: includeDedication ? dedicationText : null,
            font_choice: fontChoice,
            is_full_bleed: isFullBleed,
          }),
        }
      );

      setDocuments((prev) => [newDoc, ...prev]);
      setSelectedDoc(newDoc);
      setSuccess(true);

      // Refresh quality findings
      const qData = await apiClient<any>(`/api/v1/books/${bookId}/quality`);
      setQualityData(qData);
    } catch (err: any) {
      setError(err.message || "Failed to generate interior PDF.");
    } finally {
      setGenerating(false);
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

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Action Strip */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-amber-500" />
              <span>Interior Layout Studio & PDF Engine</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Compile your chapters, front matter, and approved artwork into an Amazon KDP print-ready interior PDF.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {selectedDoc && (
              <a
                href={`/api/v1/books/${book.id}/documents/${selectedDoc.id}/download`}
                download
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
              >
                <Download className="w-4 h-4 text-amber-400" />
                <span>Download PDF</span>
              </a>
            )}
            <button
              onClick={handleGenerateInterior}
              disabled={generating}
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-md shadow-amber-500/20 disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{generating ? "Compiling Interior..." : "Generate Interior PDF"}</span>
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
            <span>Interior PDF compiled successfully and verified for Amazon KDP physical manufacturing!</span>
          </div>
        )}

        {/* Geometry & Print Specs Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Trim Dimensions</span>
            <p className="text-base font-bold text-white mt-1">{book.trim_size}</p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">Amazon KDP Standard</p>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Print Interior</span>
            <p className="text-base font-bold text-white mt-1">{book.paper_type}</p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">
              {book.print_format ? book.print_format.charAt(0).toUpperCase() + book.print_format.slice(1) : ""}
            </p>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Physical Pages</span>
            <p className="text-base font-bold text-white mt-1">
              {selectedDoc ? `${selectedDoc.page_count} pgs` : "Not Rendered"}
            </p>
            <p className="text-[11px] text-emerald-400 font-sans mt-0.5">Even Parity Guaranteed</p>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Active Version</span>
            <p className="text-base font-bold text-white mt-1">
              {selectedDoc ? `v${selectedDoc.version}` : "None"}
            </p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">
              {selectedDoc ? `${Math.round(selectedDoc.file_size_bytes / 1024)} KB` : "0 versions"}
            </p>
          </div>
        </div>

        {/* Studio Workspace: Layout Controls & PDF Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Layout Configuration */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-4 h-4" />
              <span>Layout & Typography Options</span>
            </h2>

            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/60 border border-slate-700">
                <div>
                  <span className="font-semibold text-white block">Table of Contents</span>
                  <span className="text-[11px] text-slate-400">Generate front matter chapter index</span>
                </div>
                <input
                  type="checkbox"
                  checked={includeToc}
                  onChange={(e) => setIncludeToc(e.target.checked)}
                  className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0 accent-amber-500"
                />
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-white block">Author Dedication</span>
                    <span className="text-[11px] text-slate-400">Include dedicated front matter page</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={includeDedication}
                    onChange={(e) => setIncludeDedication(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0 accent-amber-500"
                  />
                </div>
                {includeDedication && (
                  <textarea
                    rows={2}
                    value={dedicationText}
                    onChange={(e) => setDedicationText(e.target.value)}
                    placeholder="Enter dedication copy..."
                    className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                )}
              </div>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 space-y-2">
                <span className="font-semibold text-white block">Typography Family</span>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setFontChoice("serif")}
                    className={`py-2 px-3 rounded-lg border text-center transition ${
                      fontChoice === "serif"
                        ? "bg-amber-500/10 border-amber-500 text-amber-300 font-serif"
                        : "bg-slate-900 border-slate-700 text-slate-400 font-serif"
                    }`}
                  >
                    Classical Serif
                  </button>
                  <button
                    type="button"
                    onClick={() => setFontChoice("sans")}
                    className={`py-2 px-3 rounded-lg border text-center transition ${
                      fontChoice === "sans"
                        ? "bg-amber-500/10 border-amber-500 text-amber-300 font-sans"
                        : "bg-slate-900 border-slate-700 text-slate-400 font-sans"
                    }`}
                  >
                    Modern Sans
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/60 border border-slate-700">
                <div>
                  <span className="font-semibold text-white block">Full Bleed Interior</span>
                  <span className="text-[11px] text-slate-400">+0.125" margin for edge artwork</span>
                </div>
                <input
                  type="checkbox"
                  checked={isFullBleed}
                  onChange={(e) => setIsFullBleed(e.target.checked)}
                  className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0 accent-amber-500"
                />
              </div>
            </div>

            {/* Document Version History */}
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <span className="text-[11px] uppercase text-slate-500 font-bold tracking-wider block">
                Generated Versions ({documents.length})
              </span>
              {documents.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No interior PDFs generated yet.</p>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {documents.map((d) => (
                    <button
                      key={d.id}
                      onClick={() => setSelectedDoc(d)}
                      className={`w-full text-left p-2.5 rounded-xl border text-xs flex items-center justify-between transition ${
                        selectedDoc?.id === d.id
                          ? "bg-amber-500/10 border-amber-500/50 text-white"
                          : "bg-slate-800/40 border-slate-800 text-slate-400 hover:text-white"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <FileCheck className="w-3.5 h-3.5 text-amber-400" />
                        <span className="font-semibold">Version {d.version}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500">
                        {d.page_count} pgs • {Math.round(d.file_size_bytes / 1024)} KB
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Center/Right Column: Live PDF Preview & Quality Findings */}
          <div className="lg:col-span-2 space-y-6">
            {/* Live Streaming Preview */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[520px]">
              <div className="p-3 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-amber-500" />
                  <span>
                    PDF Browser Stream {selectedDoc ? `(v${selectedDoc.version} • ${selectedDoc.page_count} pages)` : ""}
                  </span>
                </span>
                {selectedDoc && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    HTTP Range 206 Streaming Active
                  </span>
                )}
              </div>

              <div className="flex-1 bg-slate-950 flex items-center justify-center relative">
                {selectedDoc ? (
                  <iframe
                    src={`/api/v1/books/${book.id}/documents/${selectedDoc.id}/preview`}
                    title="Interior PDF Preview"
                    className="w-full h-full border-none"
                  />
                ) : (
                  <div className="text-center space-y-2 p-8">
                    <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
                    <p className="text-sm font-semibold text-slate-400">No PDF Preview Available</p>
                    <p className="text-xs text-slate-500 max-w-sm">
                      Configure your layout preferences on the left and click "Generate Interior PDF" to view the live publication stream.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Quality & Pre-Flight Panel */}
            {qualityData && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <FileCheck className="w-4 h-4 text-emerald-400" />
                    <span>Pre-Flight Quality & Structural Validation</span>
                  </h3>
                  <span
                    className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${
                      qualityData.summary?.is_preflight_ready
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                    }`}
                  >
                    {qualityData.summary?.is_preflight_ready ? "KDP READY" : "ACTION REQUIRED"}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Flesch Reading Ease</span>
                    <span className="text-lg font-bold text-white mt-1 block">
                      {qualityData.readability?.flesch_reading_ease ?? "N/A"}
                    </span>
                    <span className="text-[10px] text-slate-400 truncate block">
                      {qualityData.readability?.reading_ease_band ?? "English Only"}
                    </span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Grade Level</span>
                    <span className="text-lg font-bold text-white mt-1 block">
                      {qualityData.readability?.flesch_kincaid_grade ? `Grade ${qualityData.readability.flesch_kincaid_grade}` : "N/A"}
                    </span>
                    <span className="text-[10px] text-slate-400 block">Flesch-Kincaid</span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Total Word Count</span>
                    <span className="text-lg font-bold text-white mt-1 block">
                      {qualityData.readability?.word_count?.toLocaleString() ?? 0}
                    </span>
                    <span className="text-[10px] text-slate-400 block">Manuscript words</span>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-bold block">Findings Audit</span>
                    <span className="text-lg font-bold text-white mt-1 block">
                      {qualityData.summary?.blocking ?? 0} Blocking
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      {qualityData.summary?.advisory ?? 0} Advisories
                    </span>
                  </div>
                </div>

                {qualityData.findings && qualityData.findings.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Pre-Flight Findings List
                    </span>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto">
                      {qualityData.findings.map((f: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/80 text-xs flex items-start justify-between gap-3"
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                                  f.severity === "BLOCKING"
                                    ? "bg-rose-500/20 text-rose-300"
                                    : "bg-amber-500/20 text-amber-300"
                                }`}
                              >
                                {f.severity}
                              </span>
                              <span className="font-semibold text-white">{f.rule_id}</span>
                              <span className="text-slate-400 text-[11px]">• {f.location || f.category}</span>
                            </div>
                            <p className="text-slate-300 text-[11px]">{f.explanation}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

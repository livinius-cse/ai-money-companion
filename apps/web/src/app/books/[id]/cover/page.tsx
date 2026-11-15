"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  Palette,
  Sparkles,
  Download,
  Eye,
  CheckCircle2,
  FileCheck,
  Calculator,
  ShieldAlert,
  Image as ImageIcon,
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

interface CoverCalculation {
  format: string;
  trim_size: string;
  paper_type: string;
  interior_page_count: number;
  even_page_count: number;
  spine_coefficient: number;
  spine_width_inches: number;
  spine_width_pt: number;
  full_cover_width_inches: number;
  full_cover_width_pt: number;
  full_cover_height_inches: number;
  full_cover_height_pt: number;
  bleed_inches: number;
  bleed_pt: number;
  safe_zone_margin_inches: number;
  safe_zone_margin_pt: number;
  spine_text_eligible: boolean;
  spine_text_reason?: string | null;
  barcode_box: { x_pt: number; y_pt: number; width_pt: number; height_pt: number };
  provenance: string;
  is_supported?: boolean;
  restriction_reason?: string | null;
  is_provisional?: boolean;
  interior_document_id?: string | null;
  is_kdp_compliant_page_count?: boolean;
  min_page_warning?: string | null;
}

interface Illustration {
  id: string;
  prompt: string;
  description?: string | null;
  status: string;
  storage_key?: string | null;
}

interface BookDocument {
  id: string;
  document_type: string;
  version: number;
  storage_key: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  width_pt: number;
  height_pt: number;
  trim_size: string;
  status: string;
  created_at: string;
}

export default function CoverDesignPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [calc, setCalc] = useState<CoverCalculation | null>(null);
  const [illustrations, setIllustrations] = useState<Illustration[]>([]);
  const [documents, setDocuments] = useState<BookDocument[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<BookDocument | null>(null);

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form controls
  const [customTitle, setCustomTitle] = useState("");
  const [customSubtitle, setCustomSubtitle] = useState("");
  const [customAuthor, setCustomAuthor] = useState("");
  const [backDescription, setBackDescription] = useState("");
  const [primaryColor, setPrimaryColor] = useState("#0f172a");
  const [accentColor, setAccentColor] = useState("#f59e0b");
  const [frontArtworkId, setFrontArtworkId] = useState("");
  const [backArtworkId, setBackArtworkId] = useState("");
  const [includeSpineText, setIncludeSpineText] = useState(true);
  const [renderGuides, setRenderGuides] = useState(false);

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
      const [bookData, calcData, illsData, docsData] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<CoverCalculation>(`/api/v1/books/${bookId}/documents/cover-calculator`),
        apiClient<Illustration[]>(`/api/v1/books/${bookId}/illustrations`),
        apiClient<{ items: BookDocument[]; total: number }>(`/api/v1/books/${bookId}/documents`),
      ]);

      setBook(bookData);
      setCalc(calcData);
      setIllustrations(illsData || []);

      // Default fields from book
      setCustomTitle(bookData.title);
      setCustomSubtitle(bookData.subtitle || "");
      setCustomAuthor(user?.full_name || "Author Publisher");
      setBackDescription(bookData.topic);

      const covers = (docsData.items || []).filter((d) => d.document_type === "COVER");
      setDocuments(covers);
      if (covers.length > 0) {
        setSelectedDoc(covers[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load cover studio data.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCover = async () => {
    try {
      setGenerating(true);
      setError(null);
      setSuccess(false);

      const newDoc = await apiClient<BookDocument>(
        `/api/v1/books/${bookId}/documents/cover/generate`,
        {
          method: "POST",
          body: JSON.stringify({
            custom_front_title: customTitle.trim() || null,
            custom_front_subtitle: customSubtitle.trim() || null,
            custom_author_name: customAuthor.trim() || null,
            back_cover_description: backDescription.trim() || null,
            primary_color: primaryColor,
            accent_color: accentColor,
            front_artwork_id: frontArtworkId || null,
            back_artwork_id: backArtworkId || null,
            include_spine_text: includeSpineText,
            render_guides: renderGuides,
          }),
        }
      );

      setDocuments((prev) => [newDoc, ...prev]);
      setSelectedDoc(newDoc);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || "Failed to generate full-jacket cover PDF.");
    } finally {
      setGenerating(false);
    }
  };

  if (authLoading || loading || !book || !calc) {
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
              <Palette className="w-5 h-5 text-amber-500" />
              <span>Full-Jacket Cover Studio & Calculator</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Calculate exact spine width, configure safe zones, upload artwork, and generate an Amazon KDP compliant full-cover PDF.
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
                <span>Download Cover</span>
              </a>
            )}
            <button
              onClick={handleGenerateCover}
              disabled={
                generating ||
                book.print_format === "hardcover" ||
                calc?.is_supported === false ||
                calc?.is_provisional === true ||
                calc?.is_kdp_compliant_page_count === false
              }
              className="flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-md shadow-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              <span>
                {generating
                  ? "Generating Cover..."
                  : book.print_format === "hardcover"
                  ? "Hardcover Restricted"
                  : calc?.is_provisional
                  ? "Compile Interior PDF First"
                  : calc?.is_kdp_compliant_page_count === false
                  ? "Min 24 Pages Required"
                  : "Generate Full-Jacket Cover"}
              </span>
            </button>
          </div>
        </div>

        {calc?.is_provisional && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm flex items-start gap-3">
            <Calculator className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-white">Provisional Cover Calculation</p>
              <p className="text-xs text-slate-300 mt-1">
                These cover dimensions are provisional estimates based on target page count ({calc.interior_page_count} pages). Amazon KDP requires the cover spine to match the exact physical page count of the compiled interior. Please compile an interior PDF in Layout Studio to establish the authoritative spine width.
              </p>
            </div>
          </div>
        )}

        {calc?.is_kdp_compliant_page_count === false && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-white">KDP Page Count Requirement Not Met</p>
              <p className="text-xs text-slate-300 mt-1">
                {calc.min_page_warning || `Amazon KDP requires at least 24 pages for paperback printing. Current interior has only ${calc.interior_page_count} pages.`}
              </p>
            </div>
          </div>
        )}

        {(book.print_format === "hardcover" || calc?.is_supported === false) && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-white">Hardcover Standalone Generation Restricted</p>
              <p className="text-xs text-slate-300 mt-1">
                Amazon KDP hardcover case-laminate covers require exact manufacturing templates generated directly from the official KDP Cover Calculator (including board thickness, wrap, and hinge geometry). Automated standalone generation is restricted to prevent printer rejection. Please switch to Paperback format for verified KDP-ready full-jacket generation.
              </p>
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>Full-jacket cover PDF generated successfully with verified Amazon KDP dimensions!</span>
          </div>
        )}

        {/* Cover Mathematics Engine Summary Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Spine Thickness</span>
            <p className="text-base font-bold text-white mt-1">
              {calc.spine_width_inches.toFixed(4)}"
              <span className="text-xs text-slate-400 font-normal ml-1">({calc.spine_width_pt.toFixed(1)} pt)</span>
            </p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">{calc.even_page_count} pages • {calc.paper_type}</p>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Full Cover Dimensions</span>
            <p className="text-base font-bold text-white mt-1">
              {calc.full_cover_width_inches.toFixed(3)}" x {calc.full_cover_height_inches.toFixed(3)}"
            </p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">MediaBox: {calc.full_cover_width_pt.toFixed(1)} x {calc.full_cover_height_pt.toFixed(1)} pt</p>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Spine Text Status</span>
            <div className="mt-1">
              {calc.spine_text_eligible ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold">
                  Eligible (&ge; 80 pgs)
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-semibold">
                  Restricted (&lt; 80 pgs)
                </span>
              )}
            </div>
            <p className="text-[10px] text-slate-500 font-sans mt-1">
              {calc.spine_text_eligible ? "Safe for centered text" : "KDP prohibits spine text"}
            </p>
          </div>

          <div>
            <span className="text-[10px] uppercase text-slate-500 font-bold tracking-wider">Active Version</span>
            <p className="text-base font-bold text-white mt-1">
              {selectedDoc ? `v${selectedDoc.version}` : "None"}
            </p>
            <p className="text-[11px] text-slate-400 font-sans mt-0.5">
              {selectedDoc ? `${Math.round(selectedDoc.file_size_bytes / 1024)} KB • 1 page` : "0 versions"}
            </p>
          </div>
        </div>

        {/* Studio Workspace: Cover Form & PDF Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Form Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5">
            <h2 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <Calculator className="w-4 h-4" />
              <span>Full-Jacket Design Options</span>
            </h2>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Front Cover Title</label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Subtitle</label>
                <input
                  type="text"
                  value={customSubtitle}
                  onChange={(e) => setCustomSubtitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Author / Imprint Name</label>
                <input
                  type="text"
                  value={customAuthor}
                  onChange={(e) => setCustomAuthor(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Back Cover Description</label>
                <textarea
                  rows={3}
                  value={backDescription}
                  onChange={(e) => setBackDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Primary Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={primaryColor}
                      onChange={(e) => setPrimaryColor(e.target.value)}
                      className="w-8 h-8 rounded border-none bg-transparent cursor-pointer"
                    />
                    <span className="font-mono text-slate-400">{primaryColor}</span>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">Accent Color</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={accentColor}
                      onChange={(e) => setAccentColor(e.target.value)}
                      className="w-8 h-8 rounded border-none bg-transparent cursor-pointer"
                    />
                    <span className="font-mono text-slate-400">{accentColor}</span>
                  </div>
                </div>
              </div>

              {/* Artwork Selectors */}
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Front Cover Artwork</label>
                <select
                  value={frontArtworkId}
                  onChange={(e) => setFrontArtworkId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-white text-xs focus:outline-none"
                >
                  <option value="">No Artwork (Solid Color & Typography)</option>
                  {illustrations
                    .filter((ill) => ill.storage_key)
                    .map((ill) => (
                      <option key={ill.id} value={ill.id}>
                        {ill.prompt.substring(0, 45)}... ({ill.status})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-800/60 border border-slate-700">
                <div>
                  <span className="font-semibold text-white block">Render Preview Guides</span>
                  <span className="text-[11px] text-slate-400">Show fold and safe margin lines</span>
                </div>
                <input
                  type="checkbox"
                  checked={renderGuides}
                  onChange={(e) => setRenderGuides(e.target.checked)}
                  className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-amber-500 focus:ring-0 accent-amber-500"
                />
              </div>
            </div>

            {/* Document Version History */}
            <div className="space-y-3 pt-4 border-t border-slate-800">
              <span className="text-[11px] uppercase text-slate-500 font-bold tracking-wider block">
                Cover Versions ({documents.length})
              </span>
              {documents.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No cover PDFs generated yet.</p>
              ) : (
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
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
                        {Math.round(d.file_size_bytes / 1024)} KB
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Live Cover PDF Preview */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[520px]">
              <div className="p-3 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Eye className="w-3.5 h-3.5 text-amber-500" />
                  <span>
                    Full-Jacket PDF Preview {selectedDoc ? `(v${selectedDoc.version})` : ""}
                  </span>
                </span>
                {selectedDoc && (
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    KDP Single Page Valid
                  </span>
                )}
              </div>

              <div className="flex-1 bg-slate-950 flex items-center justify-center relative">
                {selectedDoc ? (
                  <iframe
                    src={`/api/v1/books/${book.id}/documents/${selectedDoc.id}/preview`}
                    title="Full Jacket Cover Preview"
                    className="w-full h-full border-none"
                  />
                ) : (
                  <div className="text-center space-y-2 p-8">
                    <Palette className="w-10 h-10 text-slate-600 mx-auto" />
                    <p className="text-sm font-semibold text-slate-400">No Cover Generated Yet</p>
                    <p className="text-xs text-slate-500 max-w-sm">
                      Customize your front and back cover options on the left, then click "Generate Full-Jacket Cover" to compile your print PDF.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Geometry Explanatory Banner */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3 text-xs text-slate-300">
              <h3 className="font-bold text-white text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Calculator className="w-4 h-4 text-cyan-400" />
                <span>KDP Cover Geometry & Manufacturing Guidelines</span>
              </h3>
              <p className="leading-relaxed text-slate-400">
                A full-jacket PDF is a continuous single page comprising the back cover (left), spine (center), front cover (right), plus a 0.125" bleed extending on all outer edges. Barcode reserve area (2.0" x 1.2") is preserved on the lower right of the back cover.
              </p>
              <div className="flex flex-wrap items-center gap-4 text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800">
                <span>Left Bleed: {calc.bleed_inches}"</span>
                <span>Back Cover: {((calc.full_cover_width_inches - 2 * calc.bleed_inches - calc.spine_width_inches) / 2).toFixed(3)}"</span>
                <span className="text-amber-400 font-bold">Spine: {calc.spine_width_inches.toFixed(4)}"</span>
                <span>Front Cover: {((calc.full_cover_width_inches - 2 * calc.bleed_inches - calc.spine_width_inches) / 2).toFixed(3)}"</span>
                <span>Right Bleed: {calc.bleed_inches}"</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

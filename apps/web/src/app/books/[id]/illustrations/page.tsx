"use client";

import React, { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import { BookSubNav } from "@/components/book-sub-nav";
import {
  Image as ImageIcon,
  Sparkles,
  Upload,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  X,
  FileText,
  ShieldCheck,
  Check,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  print_format: string;
  trim_size: string;
  status: string;
}

interface Chapter {
  id: string;
  chapter_number: number;
  title: string;
}

interface Illustration {
  id: string;
  book_id: string;
  chapter_id?: string | null;
  prompt: string;
  description?: string | null;
  style_preset?: string | null;
  seed?: string | null;
  position_description?: string | null;
  status: "PROMPT" | "PLACEHOLDER" | "GENERATED" | "APPROVED_FINAL";
  storage_key?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
  sha256_hash?: string | null;
  asset_source?: string | null;
  created_at: string;
}

interface IllustrationPromptItem {
  prompt: string;
  description: string;
  style_preset: string;
  suggested_placement: string;
}

export default function IllustrationStudioPage() {
  const params = useParams();
  const bookId = params.id as string;
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [book, setBook] = useState<Book | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [illustrations, setIllustrations] = useState<Illustration[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Add Placeholder Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newPrompt, setNewPrompt] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newChapterId, setNewChapterId] = useState("");
  const [newStyle, setNewStyle] = useState("modern_clean_vector");
  const [newStatus, setNewStatus] = useState<"PROMPT" | "PLACEHOLDER">("PLACEHOLDER");
  const [adding, setAdding] = useState(false);

  // AI Prompt Modal
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  const [aiTargetCount, setAiTargetCount] = useState(3);
  const [aiStylePreset, setAiStylePreset] = useState("modern_clean_vector");
  const [aiInstructions, setAiInstructions] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedPrompts, setGeneratedPrompts] = useState<IllustrationPromptItem[]>([]);

  // Approval Modal
  const [approvalTarget, setApprovalTarget] = useState<Illustration | null>(null);
  const [humanApprovedCheck, setHumanApprovedCheck] = useState(false);
  const [approving, setApproving] = useState(false);

  // Uploading state
  const [uploadingId, setUploadingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadTargetId, setActiveUploadTargetId] = useState<string | null>(null);

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
      const [bookData, chaps, ills] = await Promise.all([
        apiClient<Book>(`/api/v1/books/${bookId}`),
        apiClient<Chapter[]>(`/api/v1/books/${bookId}/chapters`),
        apiClient<Illustration[]>(`/api/v1/books/${bookId}/illustrations`),
      ]);
      setBook(bookData);
      setChapters(chaps || []);
      setIllustrations(ills || []);
    } catch (err) {
      console.error("Failed to load illustration studio:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateIllustration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPrompt.trim()) return;
    try {
      setAdding(true);
      const created = await apiClient<Illustration>(`/api/v1/books/${bookId}/illustrations`, {
        method: "POST",
        body: JSON.stringify({
          prompt: newPrompt.trim(),
          description: newDescription.trim() || null,
          chapter_id: newChapterId || null,
          style_preset: newStyle,
          status: newStatus,
        }),
      });

      setIllustrations((prev) => [created, ...prev]);
      setIsAddModalOpen(false);
      setNewPrompt("");
      setNewDescription("");
    } catch (err) {
      alert("Failed to create illustration.");
    } finally {
      setAdding(false);
    }
  };

  const handleAIPromptGenerate = async () => {
    try {
      setGenerating(true);
      const res = await apiClient<{ prompts: IllustrationPromptItem[] }>(
        `/api/v1/books/${bookId}/illustrations/generate-prompts`,
        {
          method: "POST",
          body: JSON.stringify({
            target_count: aiTargetCount,
            style_preset: aiStylePreset,
            visual_instructions: aiInstructions || null,
          }),
        }
      );
      setGeneratedPrompts(res.prompts || []);
    } catch (err) {
      alert("Failed to generate illustration prompts.");
    } finally {
      setGenerating(false);
    }
  };

  const handleAddAIPrompt = async (item: IllustrationPromptItem) => {
    try {
      const created = await apiClient<Illustration>(`/api/v1/books/${bookId}/illustrations`, {
        method: "POST",
        body: JSON.stringify({
          prompt: item.prompt,
          description: item.description,
          style_preset: item.style_preset,
          position_description: item.suggested_placement,
          status: "PROMPT",
        }),
      });

      setIllustrations((prev) => [created, ...prev]);
      setGeneratedPrompts((prev) => prev.filter((p) => p !== item));
    } catch (err) {
      alert("Failed to add prompt.");
    }
  };

  const triggerUpload = (illustrationId: string) => {
    setActiveUploadTargetId(illustrationId);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeUploadTargetId) return;

    try {
      setUploadingId(activeUploadTargetId);
      const formData = new FormData();
      formData.append("file", file);

      const updated = await apiClient<Illustration>(
        `/api/v1/books/${bookId}/illustrations/${activeUploadTargetId}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      setIllustrations((prev) =>
        prev.map((i) => (i.id === activeUploadTargetId ? updated : i))
      );
    } catch (err: any) {
      alert(err.message || "Failed to upload file. Must be valid PNG, JPEG, or WebP under 10MB.");
    } finally {
      setUploadingId(null);
      setActiveUploadTargetId(null);
    }
  };

  const handleStatusChange = async (
    ill: Illustration,
    targetStatus: "PROMPT" | "PLACEHOLDER" | "GENERATED" | "APPROVED_FINAL"
  ) => {
    if (targetStatus === "APPROVED_FINAL") {
      setApprovalTarget(ill);
      setHumanApprovedCheck(false);
      return;
    }

    try {
      const updated = await apiClient<Illustration>(
        `/api/v1/books/${bookId}/illustrations/${ill.id}/status`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status: targetStatus,
            human_approved: false,
          }),
        }
      );
      setIllustrations((prev) => prev.map((i) => (i.id === ill.id ? updated : i)));
    } catch (err: any) {
      alert(err.message || "Invalid status transition.");
    }
  };

  const handleConfirmApproval = async () => {
    if (!approvalTarget || !humanApprovedCheck) return;
    try {
      setApproving(true);
      const updated = await apiClient<Illustration>(
        `/api/v1/books/${bookId}/illustrations/${approvalTarget.id}/status`,
        {
          method: "PATCH",
          body: JSON.stringify({
            status: "APPROVED_FINAL",
            human_approved: true,
          }),
        }
      );
      setIllustrations((prev) =>
        prev.map((i) => (i.id === approvalTarget.id ? updated : i))
      );
      setApprovalTarget(null);
    } catch (err: any) {
      alert(err.message || "Failed to approve illustration.");
    } finally {
      setApproving(false);
    }
  };

  const handleDeleteIllustration = async (id: string) => {
    if (!confirm("Are you sure you want to delete this illustration and its asset file?")) {
      return;
    }
    try {
      await apiClient(`/api/v1/books/${bookId}/illustrations/${id}`, {
        method: "DELETE",
      });
      setIllustrations((prev) => prev.filter((i) => i.id !== id));
    } catch (err) {
      alert("Failed to delete illustration.");
    }
  };

  const filteredIllustrations = illustrations.filter((ill) => {
    return statusFilter === "ALL" || ill.status === statusFilter;
  });

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

      {/* Hidden file input for asset uploads */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Action Strip */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-amber-500" />
              <span>Illustration Studio & Asset Manager</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Curate illustration prompts, manage layout placeholders, upload private images, and approve final assets.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                setGeneratedPrompts([]);
                setIsAIModalOpen(true);
              }}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 transition shadow-sm"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Prompts with AI</span>
            </button>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm shadow-amber-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Add Placeholder</span>
            </button>
          </div>
        </div>

        {/* Filter Strip */}
        <div className="flex items-center gap-2 overflow-x-auto scrollbar-none pb-1">
          {["ALL", "PROMPT", "PLACEHOLDER", "GENERATED", "APPROVED_FINAL"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                statusFilter === st
                  ? "bg-amber-500 text-slate-950 shadow-sm shadow-amber-500/20"
                  : "bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Illustrations Grid */}
        {filteredIllustrations.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-16 text-center space-y-4 bg-slate-900/20">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto">
              <ImageIcon className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">No visuals found</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              {statusFilter !== "ALL"
                ? `No illustrations currently in status '${statusFilter}'.`
                : "No illustrations configured for this book yet. Click 'Generate Prompts with AI' or 'Add Placeholder' to get started."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredIllustrations.map((ill) => {
              const chap = chapters.find((c) => c.id === ill.chapter_id);
              const hasAsset = Boolean(ill.storage_key);

              return (
                <div
                  key={ill.id}
                  className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col justify-between shadow-lg"
                >
                  {/* Top Preview or Visual Placeholder */}
                  <div className="h-44 bg-slate-950 flex items-center justify-center relative border-b border-slate-800 group">
                    {hasAsset ? (
                      <img
                        src={`/api/v1/books/${bookId}/illustrations/${ill.id}/asset`}
                        alt={ill.prompt}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="text-center space-y-2 p-4">
                        <div className="w-10 h-10 rounded-xl bg-slate-800 text-slate-500 flex items-center justify-center mx-auto">
                          <ImageIcon className="w-5 h-5" />
                        </div>
                        <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider block">
                          {ill.status === "PLACEHOLDER" ? "Reserved Layout Slot" : "Prompt Only"}
                        </span>
                      </div>
                    )}

                    {/* Status Badge Tag */}
                    <div className="absolute top-3 left-3">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border backdrop-blur-md ${
                          ill.status === "APPROVED_FINAL"
                            ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                            : ill.status === "GENERATED"
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                            : ill.status === "PLACEHOLDER"
                            ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                            : "bg-slate-800/80 text-slate-300 border-slate-700"
                        }`}
                      >
                        {ill.status}
                      </span>
                    </div>

                    {/* Delete button */}
                    <button
                      onClick={() => handleDeleteIllustration(ill.id)}
                      className="absolute top-3 right-3 p-1.5 rounded-lg bg-slate-900/80 hover:bg-rose-500/80 text-slate-400 hover:text-white transition"
                      title="Delete Illustration"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Body Content */}
                  <div className="p-5 space-y-3 flex-1 flex flex-col justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                        {chap ? (
                          <span className="text-amber-400">Ch. {chap.chapter_number}</span>
                        ) : (
                          <span>General Book</span>
                        )}
                        <span>•</span>
                        <span className="truncate">{ill.style_preset || "Standard Style"}</span>
                      </div>

                      <p className="text-xs text-slate-200 line-clamp-3 leading-relaxed">
                        {ill.prompt}
                      </p>
                    </div>

                    {/* Asset details if uploaded */}
                    {hasAsset && (
                      <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-500 flex items-center justify-between font-mono">
                        <span>{ill.mime_type}</span>
                        <span>{Math.round((ill.file_size_bytes || 0) / 1024)} KB</span>
                        <span>{ill.asset_source}</span>
                      </div>
                    )}

                    {/* Action Footer */}
                    <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                      {/* Upload / Re-upload Button */}
                      <button
                        onClick={() => triggerUpload(ill.id)}
                        disabled={uploadingId === ill.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition"
                      >
                        <Upload className="w-3.5 h-3.5 text-amber-400" />
                        <span>{uploadingId === ill.id ? "Uploading..." : hasAsset ? "Replace File" : "Upload File"}</span>
                      </button>

                      {/* Status Transition Select */}
                      <select
                        value={ill.status}
                        onChange={(e) => handleStatusChange(ill, e.target.value as any)}
                        className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-300 focus:outline-none focus:border-amber-500"
                      >
                        <option value="PROMPT">PROMPT</option>
                        <option value="PLACEHOLDER">PLACEHOLDER</option>
                        <option value="GENERATED" disabled={!hasAsset}>
                          GENERATED {hasAsset ? "" : "(Needs Asset)"}
                        </option>
                        <option value="APPROVED_FINAL" disabled={!hasAsset}>
                          APPROVED_FINAL
                        </option>
                      </select>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Add Placeholder Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-bold text-white text-base">Add Visual Placeholder</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateIllustration} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Illustration Prompt *</label>
                <textarea
                  required
                  rows={3}
                  value={newPrompt}
                  onChange={(e) => setNewPrompt(e.target.value)}
                  placeholder="Describe the subject, visual composition, style, and contrast..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Associated Chapter</label>
                  <select
                    value={newChapterId}
                    onChange={(e) => setNewChapterId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none"
                  >
                    <option value="">General Book Placement</option>
                    {chapters.map((c) => (
                      <option key={c.id} value={c.id}>
                        Ch. {c.chapter_number}: {c.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Initial Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none"
                  >
                    <option value="PLACEHOLDER">PLACEHOLDER (Layout Reserved)</option>
                    <option value="PROMPT">PROMPT (Prompt Idea)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Visual Style Preset</label>
                <select
                  value={newStyle}
                  onChange={(e) => setNewStyle(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none"
                >
                  <option value="modern_clean_vector">Modern Clean Vector (Publication Standard)</option>
                  <option value="clean_minimalist_line_art">Clean Minimalist Line Art</option>
                  <option value="editorial_monochrome">Editorial Charcoal & Monochrome</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={adding}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm disabled:opacity-50"
                >
                  {adding ? "Adding..." : "Add to Studio"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Prompt Generation Modal */}
      {isAIModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-white text-base">Generate Cohesive Visual Prompts</h3>
              </div>
              <button onClick={() => setIsAIModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Generates tailored illustration prompts matching your book topic and selected style preset.
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Target Prompt Count</label>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={aiTargetCount}
                  onChange={(e) => setAiTargetCount(parseInt(e.target.value, 10))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Style Preset</label>
                <select
                  value={aiStylePreset}
                  onChange={(e) => setAiStylePreset(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-white"
                >
                  <option value="modern_clean_vector">Modern Clean Vector</option>
                  <option value="clean_minimalist_line_art">Clean Minimalist Line Art</option>
                  <option value="editorial_monochrome">Editorial Monochrome</option>
                </select>
              </div>
            </div>

            {/* Generated Prompts List */}
            {generatedPrompts.length > 0 && (
              <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
                <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                  Generated Prompts ({generatedPrompts.length})
                </h4>
                {generatedPrompts.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between text-[11px] text-amber-400 font-mono font-semibold">
                      <span>{item.suggested_placement}</span>
                      <button
                        onClick={() => handleAddAIPrompt(item)}
                        className="px-2.5 py-1 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition flex items-center gap-1"
                      >
                        <Plus className="w-3 h-3" />
                        <span>Add to Studio</span>
                      </button>
                    </div>
                    <p className="text-slate-200">{item.prompt}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setIsAIModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Done
              </button>
              <button
                onClick={handleAIPromptGenerate}
                disabled={generating}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm disabled:opacity-50 flex items-center gap-2"
              >
                {generating && <div className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />}
                <span>{generating ? "Generating..." : "Generate Prompts"}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Explicit Human Approval Confirmation Modal */}
      {approvalTarget && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-2.5 text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
              <h3 className="font-bold text-white text-base">Confirm Final Human Approval</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Transitioning this illustration asset to <strong className="text-emerald-400">APPROVED_FINAL</strong> marks it as verified and signed off for commercial Amazon KDP publication.
            </p>

            <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 flex items-start gap-2.5">
              <input
                type="checkbox"
                id="human-approval-check"
                checked={humanApprovedCheck}
                onChange={(e) => setHumanApprovedCheck(e.target.checked)}
                className="mt-0.5 w-4 h-4 rounded bg-slate-900 border-slate-700 text-emerald-500 focus:ring-0 accent-emerald-500"
              />
              <label htmlFor="human-approval-check" className="text-xs text-slate-200 select-none cursor-pointer">
                I confirm that I have reviewed the image asset, confirmed visual quality, verified copyright/license compliance, and explicitly approve it for inclusion.
              </label>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setApprovalTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmApproval}
                disabled={!humanApprovedCheck || approving}
                className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow-sm disabled:opacity-50"
              >
                {approving ? "Approving..." : "Confirm & Sign Off"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

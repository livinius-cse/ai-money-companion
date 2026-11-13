"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api-client";
import { Navbar } from "@/components/navbar";
import {
  Plus,
  BookOpen,
  Search,
  Filter,
  Layers,
  FileText,
  Calendar,
  Image as ImageIcon,
  Trash2,
  ArrowRight,
} from "lucide-react";

interface Book {
  id: string;
  title: string;
  subtitle?: string | null;
  topic: string;
  book_type: string;
  print_format: string;
  trim_size: string;
  paper_type: string;
  target_page_count: number;
  status: string;
  created_at: string;
  chapter_count: number;
  total_allocated_pages: number;
  total_word_count: number;
  illustration_count: number;
}

export default function BookPortfolioPage() {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated } = useAuth();

  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const loadBooks = async () => {
    try {
      setLoading(true);
      const res = await apiClient<{ items: Book[]; total: number }>("/api/v1/books");
      setBooks(res.items || []);
    } catch (err) {
      console.error("Failed to load books:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadBooks();
    }
  }, [isAuthenticated]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to permanently delete this book draft and its contents?")) {
      return;
    }
    try {
      setDeletingId(id);
      await apiClient(`/api/v1/books/${id}`, { method: "DELETE" });
      setBooks((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      alert("Failed to delete book.");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredBooks = books.filter((b) => {
    const matchesSearch =
      b.title.toLowerCase().includes(search.toLowerCase()) ||
      b.topic.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "ALL" || b.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  if (authLoading) return null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Header Title & Action */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-amber-500" />
              <span>Product Studio Portfolio</span>
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Create, plan, draft, and assemble publishing-ready books for Amazon KDP.
            </p>
          </div>

          <button
            onClick={() => router.push("/books/new")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20 transition"
          >
            <Plus className="w-4 h-4" />
            <span>Create New Book</span>
          </button>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search by title or topic..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-800/80 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 transition"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto scrollbar-none">
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              <span>Status:</span>
            </span>
            {["ALL", "DRAFT", "PLANNING", "IN_PROGRESS", "READY"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                  statusFilter === st
                    ? "bg-amber-500 text-slate-950 font-semibold"
                    : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Books Grid */}
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-slate-400">Loading your book portfolio...</p>
          </div>
        ) : filteredBooks.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-4 bg-slate-900/20">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-400 flex items-center justify-center mx-auto">
              <BookOpen className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">No books found</h3>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              {search || statusFilter !== "ALL"
                ? "No books match your current filters. Try resetting search criteria."
                : "You have not created any books yet. Start your publishing journey by creating your first concept."}
            </p>
            <button
              onClick={() => router.push("/books/new")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Your First Book</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredBooks.map((book) => (
              <div
                key={book.id}
                onClick={() => router.push(`/books/${book.id}`)}
                className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-5 space-y-4 cursor-pointer transition shadow-lg hover:shadow-amber-500/5 flex flex-col justify-between group"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {book.print_format} • {book.trim_size}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                        book.status === "READY"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : book.status === "PLANNING" || book.status === "IN_PROGRESS"
                          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                          : "bg-slate-800 text-slate-400 border-slate-700"
                      }`}
                    >
                      {book.status}
                    </span>
                  </div>

                  <h3 className="font-bold text-base text-white group-hover:text-amber-400 transition line-clamp-1">
                    {book.title}
                  </h3>
                  {book.subtitle && (
                    <p className="text-xs text-slate-400 line-clamp-1 italic">{book.subtitle}</p>
                  )}
                  <p className="text-xs text-slate-400 line-clamp-2">{book.topic}</p>
                </div>

                {/* Metrics Footer */}
                <div className="pt-4 border-t border-slate-800/80 space-y-3">
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-800">
                      <p className="text-[10px] text-slate-500 uppercase font-medium">Chapters</p>
                      <p className="text-sm font-bold text-white mt-0.5">{book.chapter_count}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-800">
                      <p className="text-[10px] text-slate-500 uppercase font-medium">Pages</p>
                      <p className="text-sm font-bold text-white mt-0.5">
                        {book.total_allocated_pages || book.target_page_count}
                      </p>
                    </div>
                    <div className="bg-slate-800/50 rounded-lg p-2 border border-slate-800">
                      <p className="text-[10px] text-slate-500 uppercase font-medium">Visuals</p>
                      <p className="text-sm font-bold text-white mt-0.5">{book.illustration_count}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-slate-500">
                      {book.total_word_count.toLocaleString()} total words
                    </span>
                    <div className="flex items-center gap-1 text-xs text-amber-400 font-semibold group-hover:translate-x-1 transition">
                      <span>Open Studio</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

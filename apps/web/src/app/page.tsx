"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { Navbar } from "@/components/navbar";
import {
  BookOpen,
  ShieldCheck,
  Cpu,
  Database,
  CheckCircle2,
  FolderLock,
  Layers,
  ArrowRight,
  Library,
  PenTool,
  Image as ImageIcon,
  Sparkles,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [loading, isAuthenticated, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Verifying secure session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar />

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Milestone 3 Hero Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-amber-950/20 to-slate-900 border border-amber-500/30 rounded-2xl p-6 sm:p-8 shadow-xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                <h2 className="text-xl font-bold text-white tracking-tight">
                  Milestone 3 Active: Product Studio & Content Engine
                </h2>
              </div>
              <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
                Full-lifecycle publishing engine is live. Create book concepts, generate chapter page budgets,
                draft manuscripts with offline AI assistance, and manage visual illustration assets.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => router.push("/books")}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20 transition"
              >
                <Library className="w-4 h-4" />
                <span>Open Product Studio</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          </div>
        </div>

        {/* Quick Studio Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div
            onClick={() => router.push("/books")}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-lg"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center">
                <BookOpen className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-500 group-hover:text-amber-400 transition">
                /books
              </span>
            </div>
            <h3 className="font-bold text-base text-white group-hover:text-amber-400 transition">
              Book Portfolio
            </h3>
            <p className="text-xs text-slate-400">
              Manage your active KDP titles, track manuscript word counts, and review chapter page allocations.
            </p>
          </div>

          <div
            onClick={() => router.push("/books/new")}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-lg"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
                <PenTool className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-500 group-hover:text-cyan-400 transition">
                /books/new
              </span>
            </div>
            <h3 className="font-bold text-base text-white group-hover:text-cyan-400 transition">
              New Book Wizard
            </h3>
            <p className="text-xs text-slate-400">
              Launch a new publication with topic positioning, reader avatar definition, and verified KDP trim specs.
            </p>
          </div>

          <div
            onClick={() => router.push("/books")}
            className="bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl p-6 space-y-3 cursor-pointer transition group shadow-lg"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
                <ImageIcon className="w-5 h-5" />
              </div>
              <span className="text-[11px] font-mono text-slate-500 group-hover:text-emerald-400 transition">
                Asset Hub
              </span>
            </div>
            <h3 className="font-bold text-base text-white group-hover:text-emerald-400 transition">
              Visual Asset Manager
            </h3>
            <p className="text-xs text-slate-400">
              Upload high-resolution illustration assets, generate consistent visual prompts, and enforce sign-offs.
            </p>
          </div>
        </div>

        {/* System Telemetry & Architecture Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Authentication Core</span>
              <FolderLock className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-white">Secure (HttpOnly)</p>
            <p className="text-xs text-slate-400">
              SameSite=Strict cookie storage, signed CSRF double-submit tokens, and IP sliding-window protection.
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Database Persistence</span>
              <Database className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-2xl font-bold text-white">SQLite WAL Mode</p>
            <p className="text-xs text-slate-400">
              Zero-cost local database with Write-Ahead Logging for non-blocking concurrent reads and Alembic versioning.
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI Engine Mode</span>
              <Cpu className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-white">Offline (Mock Provider)</p>
            <p className="text-xs text-slate-400">
              ₹0 initial budget architecture. Operates completely offline with zero API key requirement.
            </p>
          </div>
        </div>

        {/* Milestone Execution Track */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>KDP Publishing OS — Milestone Execution Track</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-800/80 border border-emerald-500/40 space-y-1.5">
              <div className="flex items-center justify-between text-emerald-400 font-semibold">
                <span>Milestone 1: Foundations & Auth</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-slate-400">Monorepo, Argon2 auth, HttpOnly cookies, signed CSRF, SQLite WAL.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-800/80 border border-emerald-500/40 space-y-1.5">
              <div className="flex items-center justify-between text-emerald-400 font-semibold">
                <span>Milestone 2: Mock AI & KDP Engine</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-slate-400">Offline Mock AI, Gemini fallback governance, 79 paperback & 15 hardcover specs.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-800/80 border border-amber-500/50 space-y-1.5">
              <div className="flex items-center justify-between text-amber-400 font-semibold">
                <span>Milestone 3: Product Studio</span>
                <span className="text-[10px] bg-amber-500/20 text-amber-300 font-bold px-2 py-0.5 rounded">
                  ACTIVE
                </span>
              </div>
              <p className="text-slate-400">Book Concept, Page Planner, Markdown Content Studio, Illustration Studio.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

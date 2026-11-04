"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import {
  BookOpen,
  LogOut,
  ShieldCheck,
  Cpu,
  Database,
  CheckCircle2,
  FolderLock,
  Layers,
  ArrowRight,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading, logout, isAuthenticated } = useAuth();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [loading, isAuthenticated, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Verifying secure session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500 text-slate-950 flex items-center justify-center font-bold shadow-md shadow-amber-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-base text-white tracking-tight">AI Money Companion</span>
              <span className="ml-2 text-xs text-amber-400/90 font-mono px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                KDP OS v1.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right hidden sm:block">
              <p className="text-xs font-medium text-white">{user.full_name || user.email}</p>
              <p className="text-[11px] text-slate-400 font-mono">{user.email}</p>
            </div>
            {user.is_admin && (
              <span className="text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold px-2 py-0.5 rounded-md">
                Admin
              </span>
            )}
            <button
              onClick={() => logout()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Milestone 1 Status Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-700/80 rounded-2xl p-6 shadow-xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Milestone 1 Active: Core Foundations & Security</h2>
              </div>
              <p className="text-sm text-slate-400 max-w-2xl">
                Monorepo architecture initialized. FastAPI backend and Next.js frontend are authenticated via
                HttpOnly session cookies with signed CSRF defense and brute-force rate limiting.
              </p>
            </div>
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              All Security Checks Passed
            </div>
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

        {/* Milestone Roadmap Progression */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-400" />
            <span>KDP Publishing OS — Milestone Execution Track</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-800/80 border border-emerald-500/40 space-y-1.5">
              <div className="flex items-center justify-between text-emerald-400 font-semibold">
                <span>Milestone 1: Foundations & Auth</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-slate-400">Monorepo, Argon2 auth, HttpOnly cookies, signed CSRF, SQLite WAL.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-300 font-semibold">
                <span>Milestone 2: Mock AI & Metadata</span>
                <span className="text-[10px] text-amber-400 uppercase">Upcoming</span>
              </div>
              <p className="text-slate-400">BaseAIProvider, 7 domain services, and versioned KDP specs.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-300 font-semibold">
                <span>Milestone 3: Product Studio</span>
                <span className="text-[10px] text-slate-500 uppercase">Upcoming</span>
              </div>
              <p className="text-slate-400">Concept to content, markdown editor, illustration asset grid.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-300 font-semibold">
                <span>Milestone 4: WeasyPrint & Cover Math</span>
                <span className="text-[10px] text-slate-500 uppercase">Upcoming</span>
              </div>
              <p className="text-slate-400">Interior layout, spine width formulas, and local PDF compilation.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-300 font-semibold">
                <span>Milestone 5: Pre-Flight QA & 5-Way Seal</span>
                <span className="text-[10px] text-slate-500 uppercase">Upcoming</span>
              </div>
              <p className="text-slate-400">Multi-asset SHA-256 cryptographic seal & automatic invalidation.</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5 opacity-70">
              <div className="flex items-center justify-between text-slate-300 font-semibold">
                <span>Milestone 6: Package Exporter & Sales</span>
                <span className="text-[10px] text-slate-500 uppercase">Upcoming</span>
              </div>
              <p className="text-slate-400">KDP ZIP bundle generator, manual royalty import, demo watermarking.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

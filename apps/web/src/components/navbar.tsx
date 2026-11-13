"use client";

import React from "react";
import Link from "next/navigation";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { BookOpen, LogOut, LayoutDashboard, Library, PlusCircle } from "lucide-react";

export function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();

  if (!user) return null;

  const isBooksActive = pathname.startsWith("/books");
  const isDashboardActive = pathname === "/";

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo and Nav links */}
        <div className="flex items-center gap-8">
          <div
            onClick={() => router.push("/")}
            className="flex items-center gap-3 cursor-pointer select-none"
          >
            <div className="w-9 h-9 rounded-xl bg-amber-500 text-slate-950 flex items-center justify-center font-bold shadow-md shadow-amber-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-sm sm:text-base text-white tracking-tight">
                AI Money Companion
              </span>
              <span className="ml-2 text-[10px] text-amber-400 font-mono px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 hidden sm:inline">
                KDP OS v1.0
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            <button
              onClick={() => router.push("/")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition ${
                isDashboardActive
                  ? "bg-slate-800 text-amber-400 border border-slate-700"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => router.push("/books")}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition ${
                isBooksActive
                  ? "bg-slate-800 text-amber-400 border border-slate-700"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Library className="w-4 h-4" />
              <span>Product Studio</span>
            </button>
          </nav>
        </div>

        {/* User Info & Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/books/new")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-400 text-slate-950 transition shadow-sm shadow-amber-500/20"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">New Book</span>
          </button>

          <div className="text-right hidden sm:block pl-2 border-l border-slate-800">
            <p className="text-xs font-medium text-white">{user.full_name || user.email}</p>
            <p className="text-[11px] text-slate-400 font-mono">{user.email}</p>
          </div>

          <button
            onClick={() => logout()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
            title="Sign Out"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
}

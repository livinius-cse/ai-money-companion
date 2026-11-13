"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  ChevronLeft,
  FileText,
  Calendar,
  PenTool,
  Image as ImageIcon,
  Compass,
} from "lucide-react";

interface BookSubNavProps {
  bookId: string;
  bookTitle: string;
  status?: string;
  printFormat?: string;
  trimSize?: string;
}

export function BookSubNav({
  bookId,
  bookTitle,
  status = "DRAFT",
  printFormat = "paperback",
  trimSize = "6x9",
}: BookSubNavProps) {
  const router = useRouter();
  const pathname = usePathname();

  const tabs = [
    { label: "Overview", href: `/books/${bookId}`, icon: Compass, exact: true },
    { label: "Book Concept", href: `/books/${bookId}/concept`, icon: FileText },
    { label: "Page Planner", href: `/books/${bookId}/planner`, icon: Calendar },
    { label: "Content Studio", href: `/books/${bookId}/content`, icon: PenTool },
    { label: "Illustration Studio", href: `/books/${bookId}/illustrations`, icon: ImageIcon },
  ];

  return (
    <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top meta strip */}
        <div className="py-3 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/books")}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white transition"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Portfolio</span>
            </button>
            <span className="text-slate-600">/</span>
            <h1 className="text-sm font-semibold text-white tracking-tight truncate max-w-md">
              {bookTitle || "Untitled Book"}
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              {printFormat} • {trimSize}
            </span>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                status === "APPROVED" || status === "READY"
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : status === "IN_PROGRESS" || status === "PLANNING"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  : "bg-slate-800 text-slate-400 border-slate-700"
              }`}
            >
              {status}
            </span>
          </div>
        </div>

        {/* Tab Links */}
        <div className="flex items-center gap-1 overflow-x-auto py-2 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = tab.exact
              ? pathname === tab.href
              : pathname.startsWith(tab.href);

            return (
              <button
                key={tab.href}
                onClick={() => router.push(tab.href)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                  isActive
                    ? "bg-amber-500 text-slate-950 font-semibold shadow-sm shadow-amber-500/20"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

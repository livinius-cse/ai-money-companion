"use client";

import React from "react";

interface MarkdownPreviewProps {
  content: string;
}

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  if (!content || !content.trim()) {
    return (
      <div className="py-12 text-center text-slate-500 italic text-sm">
        No content written yet. Switch to Edit mode to write Markdown.
      </div>
    );
  }

  // Parse lines into structured safe elements
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];

  let inList = false;
  let listItems: string[] = [];

  const flushList = (keyPrefix: number) => {
    if (inList && listItems.length > 0) {
      elements.push(
        <ul key={`ul-${keyPrefix}`} className="list-disc list-inside space-y-1 my-3 pl-2 text-slate-300">
          {listItems.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const renderInline = (text: string): React.ReactNode => {
    // Basic inline formatting: **bold**, *italic*, `code`
    const parts = text.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
        return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
        return <em key={i} className="italic text-slate-200">{part.slice(1, -1)}</em>;
      }
      if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
        return (
          <code key={i} className="px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 font-mono text-xs">
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      inList = true;
      listItems.push(trimmed.slice(2));
      return;
    } else {
      flushList(idx);
    }

    if (trimmed.startsWith("# ")) {
      elements.push(
        <h1 key={idx} className="text-2xl font-bold text-white mt-6 mb-3 tracking-tight border-b border-slate-800 pb-2">
          {renderInline(trimmed.slice(2))}
        </h1>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h2 key={idx} className="text-xl font-bold text-white mt-5 mb-2 tracking-tight">
          {renderInline(trimmed.slice(3))}
        </h2>
      );
    } else if (trimmed.startsWith("### ")) {
      elements.push(
        <h3 key={idx} className="text-lg font-semibold text-amber-400 mt-4 mb-2">
          {renderInline(trimmed.slice(4))}
        </h3>
      );
    } else if (trimmed.startsWith("> ")) {
      elements.push(
        <blockquote key={idx} className="border-l-4 border-amber-500/80 bg-slate-800/40 px-4 py-2 my-3 rounded-r text-slate-300 italic">
          {renderInline(trimmed.slice(2))}
        </blockquote>
      );
    } else if (trimmed === "") {
      elements.push(<div key={idx} className="h-3" />);
    } else {
      elements.push(
        <p key={idx} className="leading-relaxed text-slate-300 my-1 text-sm sm:text-base">
          {renderInline(line)}
        </p>
      );
    }
  });

  flushList(lines.length);

  return (
    <div className="prose prose-invert max-w-none text-slate-200 font-sans space-y-1">
      {elements}
    </div>
  );
}

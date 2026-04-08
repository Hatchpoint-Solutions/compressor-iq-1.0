"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

export default function UserManualPage() {
  const [content, setContent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/USER_MANUAL.md")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((t) => {
        if (!cancelled) setContent(t);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load user manual.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
          Documentation
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">CompressorIQ user manual</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Full guide for <strong>service managers</strong> and <strong>field technicians</strong>, with
          screen-by-screen descriptions. Use the links below for PDFs (offline or printing).
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <a
            href="/CompressorIQ_User_Manual.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-amber-600"
          >
            Full manual PDF (text + screenshots)
          </a>
          <a
            href="/CompressorIQ_User_Guide_Screenshots.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Screenshots PDF only
          </a>
          <a
            href="/USER_MANUAL.md"
            download="CompressorIQ_USER_MANUAL.md"
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
          >
            Download manual (.md)
          </a>
        </div>
      </header>

      {error && (
        <div className="mx-auto max-w-3xl px-6 py-8">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error} Ensure <code className="rounded bg-red-100 px-1">public/USER_MANUAL.md</code> exists
            after build.
          </div>
        </div>
      )}

      {!error && !content && (
        <div className="px-6 py-12 text-center text-sm text-slate-500">Loading manual…</div>
      )}

      {content && (
        <article className="mx-auto max-w-3xl px-6 py-10 pb-16">
          <div
            className={[
              "manual-prose text-slate-800",
              "[&_h1]:mb-4 [&_h1]:mt-10 [&_h1]:border-b [&_h1]:border-slate-200 [&_h1]:pb-2 [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:text-slate-900",
              "[&_h1:first-child]:mt-0",
              "[&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-slate-900",
              "[&_h3]:mb-2 [&_h3]:mt-6 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-slate-800",
              "[&_p]:mb-3 [&_p]:leading-relaxed",
              "[&_strong]:font-semibold [&_strong]:text-slate-900",
              "[&_ul]:mb-4 [&_ul]:list-disc [&_ul]:pl-6",
              "[&_ol]:mb-4 [&_ol]:list-decimal [&_ol]:pl-6",
              "[&_li]:mb-1",
              "[&_table]:mb-4 [&_table]:w-full [&_table]:border-collapse [&_table]:text-sm",
              "[&_th]:border [&_th]:border-slate-300 [&_th]:bg-slate-100 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left",
              "[&_td]:border [&_td]:border-slate-200 [&_td]:px-3 [&_td]:py-2",
              "[&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:text-sm",
              "[&_hr]:my-8 [&_hr]:border-slate-200",
            ].join(" ")}
          >
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        </article>
      )}
    </div>
  );
}

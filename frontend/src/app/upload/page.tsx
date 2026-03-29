"use client";

import { api } from "@/lib/api";
import { useState, useEffect, type DragEvent } from "react";

type UploadPhase = "idle" | "uploading" | "processing" | "completed" | "failed";

interface UploadRecord {
  id: string;
  filename: string;
  upload_date: string | null;
  status: string;
  records_imported: number | null;
  error_message: string | null;
}

const ACCEPT = ".xlsx,.xls,.csv";

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") return "bg-emerald-100 text-emerald-800 ring-emerald-600/20";
  if (s === "failed") return "bg-red-100 text-red-800 ring-red-600/20";
  if (s === "processing") return "bg-amber-100 text-amber-800 ring-amber-600/20";
  if (s === "uploaded") return "bg-slate-100 text-slate-700 ring-slate-500/20";
  return "bg-slate-100 text-slate-700 ring-slate-500/20";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileInputReset, setFileInputReset] = useState(0);
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [history, setHistory] = useState<UploadRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [isDragging, setIsDragging] = useState(false);

  async function loadHistory() {
    try {
      setHistoryError(null);
      const items = await api.ingestion.list();
      setHistory(items as UploadRecord[]);
    } catch (e) {
      setHistoryError(e instanceof Error ? e.message : "Failed to load upload history.");
    } finally {
      setLoadingHistory(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  function pickFile(next: File | null) {
    if (!next) {
      setFile(null);
      return;
    }
    const name = next.name.toLowerCase();
    const ok = name.endsWith(".xlsx") || name.endsWith(".xls") || name.endsWith(".csv");
    if (!ok) {
      setUploadError("Please choose a .xlsx, .xls, or .csv file.");
      return;
    }
    setUploadError(null);
    setPhase("idle");
    setFile(next);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) pickFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    setUploadError(null);
    setPhase("uploading");
    try {
      const result = (await api.ingestion.upload(file)) as UploadRecord;
      if (result.status === "processing") {
        setPhase("processing");
      } else if (result.status === "failed") {
        setPhase("failed");
        setUploadError(
          result.error_message ||
            "Import failed. The file may have an unsupported column layout."
        );
      } else {
        setPhase("completed");
      }
      setFile(null);
      setFileInputReset((k) => k + 1);
      await loadHistory();
    } catch (e) {
      setPhase("failed");
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    }
  }

  const busy = phase === "uploading" || phase === "processing";

  return (
    <div className="mx-auto max-w-4xl space-y-10 px-4 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Maintenance data upload
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Upload Excel or CSV spreadsheets to import maintenance records.
        </p>
      </div>

      <section className="space-y-4">
        <div
          role="presentation"
          onDragEnter={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            if (!e.currentTarget.contains(e.relatedTarget as Node)) {
              setIsDragging(false);
            }
          }}
          onDrop={onDrop}
          className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
            isDragging
              ? "border-blue-500 bg-blue-50/80"
              : "border-slate-300 bg-slate-50/50 hover:border-slate-400"
          }`}
        >
          <input
            key={fileInputReset}
            id="maintenance-file"
            type="file"
            accept={ACCEPT}
            className="sr-only"
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            disabled={busy}
          />
          <label
            htmlFor="maintenance-file"
            className={`cursor-pointer text-sm font-medium text-blue-700 underline-offset-2 hover:underline ${
              busy ? "pointer-events-none opacity-50" : ""
            }`}
          >
            Choose a file
          </label>
          <span className="text-sm text-slate-600"> or drag and drop here</span>
          <p className="mt-2 text-xs text-slate-500">.xlsx, .xls, or .csv</p>
          {file && (
            <p className="mt-4 truncate text-sm font-medium text-slate-800" title={file.name}>
              Selected: {file.name}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || busy}
            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {busy ? "Working…" : "Upload"}
          </button>
          {phase !== "idle" && (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-500">Status:</span>
              {phase === "uploading" && (
                <span className="inline-flex items-center gap-2 text-blue-700">
                  <span
                    className="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600"
                    aria-hidden
                  />
                  Uploading…
                </span>
              )}
              {phase === "processing" && (
                <span className="inline-flex items-center gap-2 text-amber-700">
                  <span
                    className="inline-block h-2 w-2 animate-pulse rounded-full bg-amber-600"
                    aria-hidden
                  />
                  Processing…
                </span>
              )}
              {phase === "completed" && (
                <span className="font-medium text-emerald-700">Completed</span>
              )}
              {phase === "failed" && (
                <span className="font-medium text-red-700">Failed</span>
              )}
            </div>
          )}
        </div>

        {uploadError && (
          <div
            className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            role="alert"
          >
            {uploadError}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Upload history</h2>
        {historyError && (
          <p className="mb-3 text-sm text-red-600" role="alert">
            {historyError}
          </p>
        )}
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-700">Filename</th>
                <th className="px-4 py-3 font-medium text-slate-700">Upload date</th>
                <th className="px-4 py-3 font-medium text-slate-700">Status</th>
                <th className="px-4 py-3 font-medium text-slate-700">Records imported</th>
                <th className="px-4 py-3 font-medium text-slate-700">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loadingHistory ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    Loading…
                  </td>
                </tr>
              ) : history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    No uploads yet.
                  </td>
                </tr>
              ) : (
                history.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/80">
                    <td className="max-w-[200px] truncate px-4 py-3 font-medium text-slate-900">
                      {row.filename}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                      {formatDate(row.upload_date)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${statusBadgeClass(row.status)}`}
                      >
                        {row.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 tabular-nums text-slate-700">
                      {row.records_imported != null ? row.records_imported : "—"}
                    </td>
                    <td className="max-w-[240px] truncate px-4 py-3 text-slate-600" title={row.error_message ?? ""}>
                      {row.error_message ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

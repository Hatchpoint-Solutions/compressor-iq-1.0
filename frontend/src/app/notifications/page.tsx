"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type NotificationItem } from "@/lib/api";
import { formatDate } from "@/lib/utils";

const TECH_KEY = "ciq_technician_id";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "unread">("unread");
  const [techId, setTechId] = useState<string>("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setTechId(localStorage.getItem(TECH_KEY) || "");
    }
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.notifications
      .list({
        technician_id: techId || undefined,
        unread_only: filter === "unread",
        limit: 100,
      })
      .then(setItems)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load notifications.")
      )
      .finally(() => setLoading(false));
  }, [techId, filter]);

  useEffect(() => {
    load();
  }, [load]);

  const markOne = async (id: string) => {
    await api.notifications.markRead(id);
    load();
  };

  const markAll = async () => {
    await api.notifications.markAllRead(techId || undefined);
    load();
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Notifications</h1>
          <p className="mt-1 max-w-xl text-sm text-slate-600">
            Fleet alerts (system work orders) and assignments to you. Matches the technician selected on{" "}
            <Link href="/my-work" className="font-medium text-amber-700 underline underline-offset-2">
              My work
            </Link>{" "}
            when set.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as "all" | "unread")}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          >
            <option value="unread">Unread</option>
            <option value="all">All</option>
          </select>
          <button
            type="button"
            onClick={() => void markAll()}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Mark all read
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : items.length === 0 ? (
        <div className="stat-card max-w-lg">
          <p className="text-sm text-slate-600">No notifications to show.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {items.map((n) => (
            <li
              key={n.id}
              className={`rounded-xl border bg-white p-4 shadow-sm ${
                n.read_at ? "border-slate-100 opacity-80" : "border-amber-200/80"
              }`}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">{n.category.replace("_", " ")}</p>
                  <p className="mt-1 font-semibold text-slate-900">{n.title}</p>
                  {n.body && <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{n.body}</p>}
                  <p className="mt-2 text-xs text-slate-400">{formatDate(n.created_at)}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  {n.work_order_id && (
                    <Link
                      href="/work-orders"
                      className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-200"
                    >
                      Work orders
                    </Link>
                  )}
                  {!n.read_at && (
                    <button
                      type="button"
                      onClick={() => void markOne(n.id)}
                      className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600"
                    >
                      Mark read
                    </button>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

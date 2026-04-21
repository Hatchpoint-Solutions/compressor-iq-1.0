"use client";

import { api, type ServiceEvent, type ServiceEventDetail, type PaginatedResponse } from "@/lib/api";
import {
  formatDate,
  formatCurrency,
  formatNumber,
  categoryLabel,
  categoryBadgeClass,
} from "@/lib/utils";
import { useState, useEffect, useLayoutEffect, useCallback, useRef, Fragment, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

const PAGE_SIZE = 15;

function truncate(text: string | null, max: number): string {
  if (!text) return "—";
  if (text.length <= max) return text;
  return `${text.slice(0, max)}…`;
}

function ServiceRecordsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlEventId = searchParams.get("event");
  const urlUnitHint = searchParams.get("unit") ?? "";

  const [draftSearch, setDraftSearch] = useState("");
  const [draftCategory, setDraftCategory] = useState("");
  const [draftDateFrom, setDraftDateFrom] = useState("");
  const [draftDateTo, setDraftDateTo] = useState("");

  const [activeSearch, setActiveSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("");
  const [activeDateFrom, setActiveDateFrom] = useState("");
  const [activeDateTo, setActiveDateTo] = useState("");
  const [activeCompressorId, setActiveCompressorId] = useState("");

  const [page, setPage] = useState(1);
  const [data, setData] = useState<PaginatedResponse<ServiceEvent> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [categories, setCategories] = useState<string[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);

  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ServiceEventDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [genLoadingId, setGenLoadingId] = useState<string | null>(null);
  const categoriesLoadGen = useRef(0);
  const listLoadGen = useRef(0);
  const detailLoadGen = useRef(0);

  useEffect(() => {
    const gen = ++categoriesLoadGen.current;
    (async () => {
      try {
        const list = await api.events.categories();
        if (gen === categoriesLoadGen.current) setCategories(list);
      } catch {
        if (gen === categoriesLoadGen.current) setCategories([]);
      } finally {
        if (gen === categoriesLoadGen.current) setCategoriesLoading(false);
      }
    })();
  }, []);

  /** Sync filters and expanded row from URL (dashboard deep links, browser back/forward). */
  useLayoutEffect(() => {
    const cat = searchParams.get("category") ?? "";
    const comp = searchParams.get("compressor_id") ?? "";
    setDraftCategory(cat);
    setActiveCategory(cat);
    setActiveCompressorId(comp);
    const ev = searchParams.get("event");
    setExpandedId(ev);
  }, [searchParams]);

  useEffect(() => {
    if (urlEventId) setPage(1);
  }, [urlEventId]);

  const listParams = useCallback((): Record<string, string> => {
    const p: Record<string, string> = {
      page: String(page),
      page_size: String(PAGE_SIZE),
    };
    if (urlEventId) {
      p.event_id = urlEventId;
      return p;
    }
    if (activeSearch.trim()) p.search = activeSearch.trim();
    if (activeCategory) p.event_category = activeCategory;
    if (activeDateFrom) p.date_from = activeDateFrom;
    if (activeDateTo) p.date_to = activeDateTo;
    if (activeCompressorId) p.compressor_id = activeCompressorId;
    return p;
  }, [
    page,
    activeSearch,
    activeCategory,
    activeDateFrom,
    activeDateTo,
    activeCompressorId,
    urlEventId,
  ]);

  useEffect(() => {
    const gen = ++listLoadGen.current;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await api.events.list(listParams());
        if (gen === listLoadGen.current) setData(res);
      } catch (e) {
        if (gen === listLoadGen.current)
          setError(e instanceof Error ? e.message : "Failed to load events");
      } finally {
        if (gen === listLoadGen.current) setLoading(false);
      }
    })();
  }, [listParams]);

  useEffect(() => {
    if (!expandedId) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    const gen = ++detailLoadGen.current;
    setDetailLoading(true);
    setDetailError(null);
    (async () => {
      try {
        const ev = await api.events.get(expandedId);
        if (gen === detailLoadGen.current) setDetail(ev);
      } catch (e) {
        if (gen === detailLoadGen.current)
          setDetailError(e instanceof Error ? e.message : "Failed to load event");
      } finally {
        if (gen === detailLoadGen.current) setDetailLoading(false);
      }
    })();
  }, [expandedId]);

  function handleSearch() {
    setActiveSearch(draftSearch);
    setActiveCategory(draftCategory);
    setActiveDateFrom(draftDateFrom);
    setActiveDateTo(draftDateTo);
    setPage(1);
  }

  function handleClear() {
    setDraftSearch("");
    setDraftCategory("");
    setDraftDateFrom("");
    setDraftDateTo("");
    setActiveSearch("");
    setActiveCategory("");
    setActiveDateFrom("");
    setActiveDateTo("");
    setActiveCompressorId("");
    setPage(1);
    setExpandedId(null);
    router.replace("/service-records");
  }

  function toggleView(id: string) {
    setExpandedId((prev) => {
      if (prev === id) {
        if (searchParams.get("event")) {
          const sp = new URLSearchParams(searchParams.toString());
          sp.delete("event");
          const qs = sp.toString();
          router.replace(qs ? `/service-records?${qs}` : "/service-records");
        }
        return null;
      }
      return id;
    });
  }

  function clearEventDeepLink() {
    const sp = new URLSearchParams(searchParams.toString());
    sp.delete("event");
    const qs = sp.toString();
    router.replace(qs ? `/service-records?${qs}` : "/service-records");
    setExpandedId(null);
  }

  async function handleGenerate(eventId: string) {
    setGenLoadingId(eventId);
    try {
      const rec = await api.recommendations.generate(eventId);
      router.push(`/workflow/${rec.id}`);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Could not generate recommendation");
    } finally {
      setGenLoadingId(null);
    }
  }

  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = data?.items ?? [];

  const pageNumbers: number[] = [];
  const windowSize = 5;
  let start = Math.max(1, page - Math.floor(windowSize / 2));
  let end = Math.min(totalPages, start + windowSize - 1);
  if (end - start < windowSize - 1) start = Math.max(1, end - windowSize + 1);
  for (let i = start; i <= end; i++) pageNumbers.push(i);

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              Service Records
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Search and review maintenance service events.
            </p>
            {urlEventId && (
              <div className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-950">
                <span>
                  Opened a specific service event from the dashboard — details are expanded below.
                </span>
                <button
                  type="button"
                  onClick={clearEventDeepLink}
                  className="rounded-md bg-white px-3 py-1 text-xs font-medium text-amber-900 shadow-sm ring-1 ring-amber-300/80 transition hover:bg-amber-100"
                >
                  Show all records
                </button>
              </div>
            )}
            {!urlEventId && activeCompressorId && (
              <p className="mt-2 text-sm text-slate-600">
                Showing events for compressor{" "}
                <span className="font-mono font-medium text-slate-900">
                  {urlUnitHint || activeCompressorId.slice(0, 8)}
                </span>
                .{" "}
                <button
                  type="button"
                  onClick={() => {
                    const sp = new URLSearchParams(searchParams.toString());
                    sp.delete("compressor_id");
                    sp.delete("unit");
                    const qs = sp.toString();
                    router.replace(qs ? `/service-records?${qs}` : "/service-records");
                    setActiveCompressorId("");
                  }}
                  className="font-medium text-amber-800 underline decoration-amber-300 underline-offset-2 hover:text-amber-950"
                >
                  Clear compressor filter
                </button>
              </p>
            )}
          </div>
          <Link
            href="/"
            className="text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-2 hover:text-slate-900"
          >
            ← Home
          </Link>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
            <div className="lg:col-span-2">
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                Search notes / description
              </label>
              <input
                type="search"
                value={draftSearch}
                onChange={(e) => setDraftSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Keywords…"
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none ring-slate-200 placeholder:text-slate-400 focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                Category
              </label>
              <select
                value={draftCategory}
                onChange={(e) => setDraftCategory(e.target.value)}
                disabled={categoriesLoading}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-200 disabled:opacity-60"
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {categoryLabel(c)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                From
              </label>
              <input
                type="date"
                value={draftDateFrom}
                onChange={(e) => setDraftDateFrom(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">
                To
              </label>
              <input
                type="date"
                value={draftDateTo}
                onChange={(e) => setDraftDateTo(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-slate-300 focus:ring-2 focus:ring-slate-200"
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                type="button"
                onClick={handleSearch}
                className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-900"
              >
                Search
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80">
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Date
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Order #
                  </th>
                  <th className="min-w-[180px] px-4 py-3 font-semibold text-slate-700">
                    Description
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Category
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Activity Type
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Run Hours
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Cost
                  </th>
                  <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-700">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      Loading…
                    </td>
                  </tr>
                )}
                {!loading && error && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-red-600">
                      {error}
                    </td>
                  </tr>
                )}
                {!loading && !error && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-slate-500">
                      No service events match your filters.
                    </td>
                  </tr>
                )}
                {!loading &&
                  !error &&
                  items.map((ev) => (
                    <Fragment key={ev.id}>
                      <tr
                        className="border-b border-slate-100 transition hover:bg-slate-50/80"
                      >
                        <td className="whitespace-nowrap px-4 py-3 text-slate-800">
                          {formatDate(ev.event_date)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-700">
                          {ev.order_number || "—"}
                        </td>
                        <td className="max-w-[240px] px-4 py-3 text-slate-700">
                          {truncate(ev.order_description, 60)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <span className={categoryBadgeClass(ev.event_category)}>
                            {categoryLabel(ev.event_category)}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                          {ev.maintenance_activity_type || "—"}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 tabular-nums text-slate-800">
                          {formatNumber(ev.run_hours_at_event)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 tabular-nums text-slate-800">
                          {formatCurrency(ev.order_cost)}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <Link
                              href="#"
                              onClick={(e) => {
                                e.preventDefault();
                                toggleView(ev.id);
                              }}
                              className="text-sm font-medium text-slate-800 underline decoration-slate-300 underline-offset-2 hover:text-slate-950"
                            >
                              {expandedId === ev.id ? "Hide" : "View"}
                            </Link>
                            <button
                              type="button"
                              disabled={genLoadingId === ev.id}
                              onClick={() => handleGenerate(ev.id)}
                              className="rounded-md border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900 transition hover:bg-amber-100 disabled:opacity-50"
                            >
                              {genLoadingId === ev.id ? "…" : "Get Recommendation"}
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedId === ev.id && (
                        <tr key={`${ev.id}-detail`} className="bg-slate-50/90">
                          <td colSpan={8} className="border-b border-slate-200 px-4 py-5">
                            {detailLoading && (
                              <p className="text-sm text-slate-500">Loading details…</p>
                            )}
                            {!detailLoading && detailError && (
                              <p className="text-sm text-red-600">{detailError}</p>
                            )}
                            {!detailLoading && !detailError && detail && (
                              <div className="space-y-5">
                                <div>
                                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    Technician notes
                                  </h3>
                                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                                    {(detail.technician_notes_clean ?? detail.technician_notes_raw)?.trim()
                                      ? (detail.technician_notes_clean ?? detail.technician_notes_raw)
                                      : "—"}
                                  </p>
                                </div>
                                <div>
                                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                    Maintenance actions
                                  </h3>
                                  {detail.actions && detail.actions.length > 0 ? (
                                    <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
                                      {detail.actions.map((a) => (
                                        <li
                                          key={a.id}
                                          className="px-4 py-3 text-sm text-slate-800"
                                        >
                                          <div className="flex flex-wrap gap-x-4 gap-y-1">
                                            <span className="font-medium text-slate-900">
                                              {a.action_type_raw || "Action"}
                                            </span>
                                            {a.component && (
                                              <span className="text-slate-600">
                                                {a.component}
                                              </span>
                                            )}
                                            {a.technician_name_raw && (
                                              <span className="text-slate-500">
                                                {a.technician_name_raw}
                                              </span>
                                            )}
                                          </div>
                                          {a.description && (
                                            <p className="mt-1 text-slate-600">
                                              {a.description}
                                            </p>
                                          )}
                                          <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-500">
                                            {a.action_date && (
                                              <span>{formatDate(a.action_date)}</span>
                                            )}
                                            {a.run_hours_at_action != null && (
                                              <span>
                                                {formatNumber(a.run_hours_at_action)} h
                                              </span>
                                            )}
                                          </div>
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="mt-2 text-sm text-slate-500">
                                      No maintenance actions recorded.
                                    </p>
                                  )}
                                </div>
                                <div>
                                  <button
                                    type="button"
                                    disabled={genLoadingId === ev.id}
                                    onClick={() => handleGenerate(ev.id)}
                                    className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-slate-900 disabled:opacity-50"
                                  >
                                    {genLoadingId === ev.id
                                      ? "Generating…"
                                      : "Generate Recommendation"}
                                  </button>
                                </div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
              </tbody>
            </table>
          </div>

          {!loading && !error && totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 bg-white px-4 py-3">
              <p className="text-sm text-slate-600">
                Showing{" "}
                <span className="font-medium text-slate-900">
                  {total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1}
                </span>
                –
                <span className="font-medium text-slate-900">
                  {Math.min(page * PAGE_SIZE, total)}
                </span>{" "}
                of <span className="font-medium text-slate-900">{total}</span>
              </p>
              <div className="flex flex-wrap items-center gap-1">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Prev
                </button>
                {start > 1 && (
                  <>
                    <button
                      type="button"
                      onClick={() => setPage(1)}
                      className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      1
                    </button>
                    {start > 2 && (
                      <span className="px-2 text-slate-400">…</span>
                    )}
                  </>
                )}
                {pageNumbers.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setPage(n)}
                    className={
                      n === page
                        ? "rounded-md bg-slate-800 px-3 py-1.5 text-sm font-medium text-white"
                        : "rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                    }
                  >
                    {n}
                  </button>
                ))}
                {end < totalPages && (
                  <>
                    {end < totalPages - 1 && (
                      <span className="px-2 text-slate-400">…</span>
                    )}
                    <button
                      type="button"
                      onClick={() => setPage(totalPages)}
                      className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      {totalPages}
                    </button>
                  </>
                )}
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ServiceRecordsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 p-6 md:p-8">
          <div className="mx-auto max-w-7xl animate-pulse text-slate-500">
            Loading service records…
          </div>
        </div>
      }
    >
      <ServiceRecordsContent />
    </Suspense>
  );
}

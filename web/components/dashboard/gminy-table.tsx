/**
 * PL gminy deep-dive table.
 *
 * Sortable, filterable list of every Polish gmina with locker density.
 * Backed by TanStack Table v8 (the only frontend lib pulling its weight
 * beyond the core stack — it does column sorting, header click handlers,
 * pagination state). Server returns up to 2,477 rows from listGminy;
 * pagination is purely client-side. Voivodeship filter is a multi-select
 * combobox; population/locker filters are range inputs.
 */
"use client";

import {
  type ColumnDef,
  type SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { DensityGmina } from "@/lib/api";
import { fmt2, fmtInt } from "@/lib/format";

type Row = DensityGmina & { rank: number };

const POP_STEP = 500;
const POP_MAX = 50_000;

export function GminyTable({ rows }: { rows: DensityGmina[] }) {
  const voivodeships = useMemo(() => {
    const seen = new Set<string>();
    for (const r of rows) if (r.voivodeship) seen.add(r.voivodeship);
    return [...seen].sort();
  }, [rows]);

  const baseRows: Row[] = useMemo(
    () =>
      rows
        .filter((r) => r.lockers_per_10k != null)
        .map((r, i) => ({ ...r, rank: i + 1 })),
    [rows],
  );

  const [selectedVoivs, setSelectedVoivs] = useState<Set<string>>(
    () => new Set(voivodeships),
  );
  const [minPop, setMinPop] = useState(5000);
  const [search, setSearch] = useState("");
  const [sorting, setSorting] = useState<SortingState>([
    { id: "lockers_per_10k", desc: true },
  ]);
  const [voivMenuOpen, setVoivMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Re-seed selection when the voivodeship list changes (initial load).
  useEffect(() => {
    setSelectedVoivs(new Set(voivodeships));
  }, [voivodeships]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) setVoivMenuOpen(false);
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return baseRows.filter((r) => {
      if (r.voivodeship && !selectedVoivs.has(r.voivodeship)) return false;
      if (r.population < minPop) return false;
      if (needle && !r.name.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [baseRows, selectedVoivs, minPop, search]);

  const maxDensity = useMemo(
    () =>
      filtered.length > 0
        ? Math.max(...filtered.map((r) => r.lockers_per_10k ?? 0))
        : 1,
    [filtered],
  );

  const columns = useMemo<ColumnDef<Row>[]>(
    () => [
      {
        id: "rank",
        accessorFn: (r, i) => i + 1,
        header: "#",
        cell: (info) => (
          <span
            className="tnum"
            style={{ color: "var(--fg-subtle)" }}
          >
            {info.row.index + 1}
          </span>
        ),
        enableSorting: false,
        size: 36,
      },
      {
        accessorKey: "name",
        header: "Gmina",
        cell: (info) => info.getValue<string>(),
      },
      {
        accessorKey: "voivodeship",
        header: "Voivodeship",
        cell: (info) => (
          <span
            className="mono"
            style={{ color: "var(--fg-muted)", fontSize: 11 }}
          >
            {info.getValue<string | null>() ?? "—"}
          </span>
        ),
      },
      {
        accessorKey: "n_lockers",
        header: "Lockers",
        cell: (info) => (
          <span className="tnum">{fmtInt(info.getValue<number>())}</span>
        ),
      },
      {
        accessorKey: "population",
        header: "Population",
        cell: (info) => (
          <span className="tnum">{fmtInt(info.getValue<number>())}</span>
        ),
      },
      {
        accessorKey: "lockers_per_10k",
        header: "Lockers / 10k",
        cell: (info) => {
          const v = info.getValue<number | null>();
          if (v == null) return <span style={{ color: "var(--fg-subtle)" }}>—</span>;
          const pct = (v / maxDensity) * 100;
          return (
            <span
              className="tnum"
              style={{
                color: "var(--accent)",
                fontWeight: 500,
                letterSpacing: "-0.005em",
              }}
            >
              <span
                className="inline-block align-[2px] mr-2.5 relative"
                style={{
                  width: 36,
                  height: 4,
                  background: "var(--bg-surface-3)",
                }}
              >
                <span
                  className="absolute left-0 top-0 bottom-0"
                  style={{
                    width: `${pct.toFixed(1)}%`,
                    background: "var(--accent)",
                  }}
                />
              </span>
              {fmt2(v)}
            </span>
          );
        },
      },
    ],
    [maxDensity],
  );

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const voivSummary = (() => {
    const n = selectedVoivs.size;
    if (n === voivodeships.length)
      return (
        <>
          All <span className="mono">({voivodeships.length})</span>
        </>
      );
    if (n === 0) return "None selected";
    if (n <= 2) return [...selectedVoivs].join(", ");
    return (
      <>
        <span className="mono">{n}</span> selected
      </>
    );
  })();

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-6 flex-wrap">
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 22,
            fontWeight: 300,
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
          }}
        >
          Polish gminy — density deep-dive
        </h2>
        <p style={{ fontSize: 12.5, color: "var(--fg-muted)" }}>
          Default sort: lockers per 10k, descending. Filters narrow the working set; sort headers re-rank.
        </p>
      </div>

      <article className="panel overflow-visible">
        {/* Filters */}
        <header
          className="table-filters-row grid items-end gap-4 px-5 py-3.5 grid-cols-1 md:grid-cols-2 lg:[grid-template-columns:240px_1fr_240px_auto]"
          style={{ borderBottom: "1px solid var(--border-subtle)" }}
        >
          <div className="flex flex-col gap-1 min-w-0 relative" ref={menuRef}>
            <label
              className="uppercase"
              style={{
                fontSize: 10.5,
                letterSpacing: "0.06em",
                color: "var(--fg-subtle)",
              }}
            >
              Voivodeship
            </label>
            <button
              type="button"
              className="w-full flex items-center justify-between"
              onClick={() => setVoivMenuOpen((v) => !v)}
              style={{
                padding: "7px 10px",
                background: "var(--bg-inset)",
                border: "1px solid var(--border-default)",
                color: "var(--fg-default)",
                fontSize: 12.5,
                textAlign: "left",
                cursor: "pointer",
              }}
            >
              <span>{voivSummary}</span>
              <ChevronDown size={12} style={{ color: "var(--fg-muted)" }} />
            </button>
            {voivMenuOpen && (
              <div
                className="absolute z-20 left-0 right-0 overflow-y-auto"
                style={{
                  top: "calc(100% + 4px)",
                  background: "var(--bg-surface-2)",
                  border: "1px solid var(--border-default)",
                  padding: 6,
                  maxHeight: 280,
                }}
              >
                <div
                  className="flex justify-between mb-1 pb-1"
                  style={{ borderBottom: "1px solid var(--border-subtle)" }}
                >
                  <button
                    className="mono"
                    style={{
                      fontSize: 11,
                      color: "var(--fg-muted)",
                      padding: "4px 8px",
                    }}
                    onClick={() => setSelectedVoivs(new Set(voivodeships))}
                  >
                    Select all
                  </button>
                  <button
                    className="mono"
                    style={{
                      fontSize: 11,
                      color: "var(--fg-muted)",
                      padding: "4px 8px",
                    }}
                    onClick={() => setSelectedVoivs(new Set())}
                  >
                    Clear
                  </button>
                </div>
                {voivodeships.map((v) => {
                  const checked = selectedVoivs.has(v);
                  return (
                    <label
                      key={v}
                      className="flex items-center gap-2 px-2 py-1.5 cursor-pointer"
                      style={{ fontSize: 12.5, color: "var(--fg-default)" }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          setSelectedVoivs((prev) => {
                            const next = new Set(prev);
                            if (e.target.checked) next.add(v);
                            else next.delete(v);
                            return next;
                          });
                        }}
                        style={{ accentColor: "var(--accent)" }}
                      />
                      <span>{v}</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-1 min-w-0">
            <label
              htmlFor="pop-slider"
              className="uppercase flex justify-between"
              style={{
                fontSize: 10.5,
                letterSpacing: "0.06em",
                color: "var(--fg-subtle)",
              }}
            >
              <span>Minimum population</span>
              <span className="mono" style={{ color: "var(--fg-muted)" }}>
                {fmtInt(minPop)}
              </span>
            </label>
            <input
              id="pop-slider"
              type="range"
              min={0}
              max={POP_MAX}
              step={POP_STEP}
              value={minPop}
              onChange={(e) => setMinPop(parseInt(e.target.value, 10))}
              suppressHydrationWarning
              style={{
                width: "100%",
                height: "4px",
                background: "var(--bg-inset)",
                border: "1px solid var(--border-default)",
                marginTop: "14px",
                accentColor: "var(--accent)",
              }}
            />
          </div>

          <div className="flex flex-col gap-1 min-w-0">
            <label
              htmlFor="search"
              className="uppercase"
              style={{
                fontSize: 10.5,
                letterSpacing: "0.06em",
                color: "var(--fg-subtle)",
              }}
            >
              Search
            </label>
            <input
              id="search"
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Gmina name…"
              autoComplete="off"
              suppressHydrationWarning
              style={{
                background: "var(--bg-inset)",
                border: "1px solid var(--border-default)",
                padding: "7px 10px",
                fontSize: "12.5px",
                color: "var(--fg-default)",
                outline: "none",
              }}
            />
          </div>

          <div
            className="mono"
            style={{ fontSize: 11, color: "var(--fg-muted)" }}
          >
            {fmtInt(filtered.length)} of {fmtInt(baseRows.length)} rows
          </div>
        </header>

        <div className="overflow-x-auto" style={{ maxHeight: 540 }}>
          <table
            className="w-full"
            style={{ borderCollapse: "collapse", fontSize: 12.5 }}
          >
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((h) => {
                    const isSorted = h.column.getIsSorted();
                    const numeric =
                      h.column.id === "n_lockers" ||
                      h.column.id === "population" ||
                      h.column.id === "lockers_per_10k";
                    return (
                      <th
                        key={h.id}
                        onClick={h.column.getCanSort() ? h.column.getToggleSortingHandler() : undefined}
                        className={`uppercase select-none ${
                          h.column.getCanSort() ? "cursor-pointer" : ""
                        }`}
                        style={{
                          padding: "9px 14px",
                          textAlign: numeric ? "right" : "left",
                          background: "var(--bg-surface-2)",
                          borderBottom: "1px solid var(--border-subtle)",
                          fontSize: 10.5,
                          fontWeight: 500,
                          letterSpacing: "0.06em",
                          color: isSorted ? "var(--accent)" : "var(--fg-muted)",
                          position: "sticky",
                          top: 0,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {isSorted === "asc" && (
                          <ChevronUp size={10} className="inline ml-1 align-baseline" />
                        )}
                        {isSorted === "desc" && (
                          <ChevronDown size={10} className="inline ml-1 align-baseline" />
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="text-center"
                    style={{
                      padding: 24,
                      color: "var(--fg-subtle)",
                      fontSize: 12,
                    }}
                  >
                    No gminy match the current filter — try lowering thresholds.
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="transition-colors"
                    style={{ borderBottom: "1px solid var(--border-subtle)" }}
                  >
                    {row.getVisibleCells().map((cell) => {
                      const numeric =
                        cell.column.id === "n_lockers" ||
                        cell.column.id === "population" ||
                        cell.column.id === "lockers_per_10k" ||
                        cell.column.id === "rank";
                      return (
                        <td
                          key={cell.id}
                          style={{
                            padding: "9px 14px",
                            textAlign: numeric ? "right" : "left",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <footer
          className="px-5 py-2.5"
          style={{
            borderTop: "1px solid var(--border-subtle)",
            fontSize: 11,
            color: "var(--fg-subtle)",
          }}
        >
          Joined against <span className="mono">mv_density_gmina</span> ·
          {" "}lockers/10k normalized over GUS BDL 2024 population.
        </footer>
      </article>
    </section>
  );
}

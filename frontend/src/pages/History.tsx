import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Inbox, RotateCw, Search, Trash2, X } from "lucide-react";
import { deleteAnalysis, getAnalysis, getStatistics, listHistory } from "../lib/api";
import type { AnalysisDetail, HistoryItem, Statistics } from "../lib/types";
import { Badge, Card } from "../components/atoms";
import { confidenceTheme, labelTheme, scoreTheme, timeAgo, titleCase } from "../lib/ui";
import { ScoreGauge } from "../components/results/ScoreGauge";
import { IssueList } from "../components/results/IssueList";
import { QualityRadar } from "../components/results/QualityRadar";
import { Forensics } from "../components/results/Forensics";
import { ImageInspector } from "../components/results/ImageInspector";

const LABELS = ["", "EXCELLENT", "ACCEPTABLE", "DEGRADED", "POTENTIALLY_DEFECTIVE"];

function DetailModal({ id, onClose }: { id: string; onClose: () => void }) {
  const [d, setD] = useState<AnalysisDetail | null>(null);
  useEffect(() => { getAnalysis(id).then(setD).catch(() => onClose()); }, [id, onClose]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!d) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={`Analysis of ${d.filename}`}
        className="my-8 w-full max-w-3xl santhra-fade" onClick={(e) => e.stopPropagation()}>
        <Card className="p-6">
          <div className="mb-4 flex items-start justify-between">
            <div className="flex items-center gap-4">
              <ScoreGauge score={d.quality_score} size={110} />
              <div>
                <p className="font-semibold">{d.filename}</p>
                <p className="text-xs text-slate-400">{d.image.width}×{d.image.height} · {d.analysis_time_ms} ms</p>
                <div className="mt-2 flex gap-2">
                  <Badge className={labelTheme(d.quality_label)}>{titleCase(d.quality_label)}</Badge>
                  <Badge className={confidenceTheme(d.overall_confidence)}>{d.overall_confidence}</Badge>
                </div>
              </div>
            </div>
            <button onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-white/10"><X className="h-5 w-5" /></button>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <ImageInspector original={d.thumbnail_url} heatmap={d.heatmap_url} problem={d.problem_regions_url}
              heatmapMethod="Grad-CAM" problemMethod="CV / anomaly" />
            <div><QualityRadar dimensions={d.dimensions} /></div>
          </div>
          <div className="mt-5"><IssueList issues={d.issues} /></div>
          <p className="mt-5 rounded-xl bg-slate-100 p-3 text-sm text-slate-600 dark:bg-white/5 dark:text-slate-300">{d.narrative}</p>
          {d.forensics?.length > 0 && <div className="mt-4"><Forensics cards={d.forensics} /></div>}
        </Card>
      </div>
    </div>
  );
}

export function History() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [label, setLabel] = useState("");
  const [sort, setSort] = useState("created_at");
  const [open, setOpen] = useState<string | null>(null);
  const [stats, setStats] = useState<Statistics | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await listHistory({ search, label, sort, order: "desc", limit: 60 });
      setItems(r.items); setTotal(r.total);
      getStatistics().then(setStats).catch(() => setStats(null));
    } catch (e) {
      // Distinguish a real failure from a genuinely empty history.
      setError(e instanceof Error ? e.message : "Could not load history.");
      setItems([]); setTotal(0);
    } finally { setLoading(false); }
  }, [search, label, sort]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function remove(id: string) {
    if (!window.confirm("Delete this analysis? This also removes its stored images and cannot be undone.")) return;
    try {
      await deleteAnalysis(id);
      setItems((xs) => xs.filter((x) => x.id !== id));
      setTotal((t) => Math.max(0, t - 1));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Analysis History <span className="text-sm font-normal text-slate-400">({total})</span></h2>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search filename…"
              className="w-44 rounded-lg border border-slate-200 bg-white py-2 pl-8 pr-3 text-sm outline-none focus:border-brand-400 dark:border-white/10 dark:bg-white/5" />
          </div>
          <select value={label} onChange={(e) => setLabel(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm dark:border-white/10 dark:bg-white/5">
            {LABELS.map((l) => <option key={l} value={l}>{l ? titleCase(l) : "All labels"}</option>)}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-2 text-sm dark:border-white/10 dark:bg-white/5">
            <option value="created_at">Newest</option>
            <option value="quality_score">Score</option>
            <option value="filename">Name</option>
          </select>
        </div>
      </div>

      {stats && stats.total > 0 && !error && (
        <div className="flex flex-wrap gap-6 rounded-xl border border-slate-200 bg-white/60 px-4 py-3 text-sm dark:border-white/10 dark:bg-white/5">
          <span className="text-slate-400">Total analysed <b className="ml-1 text-slate-700 dark:text-slate-200 tabular-nums">{stats.total}</b></span>
          <span className="text-slate-400">Average score <b className="ml-1 text-slate-700 dark:text-slate-200 tabular-nums">{stats.average_score ?? "-"}</b></span>
          <span className="text-slate-400">Review rate <b className="ml-1 text-slate-700 dark:text-slate-200 tabular-nums">{Math.round(stats.review_rate * 100)}%</b></span>
        </div>
      )}

      {loading ? (
        <p className="py-16 text-center text-sm text-slate-400">Loading…</p>
      ) : error ? (
        <Card className="flex flex-col items-center gap-3 py-16 text-center">
          <AlertTriangle className="h-10 w-10 text-amber-500" />
          <p className="text-sm text-slate-500 dark:text-slate-300">Could not load history: {error}</p>
          <button onClick={load} className="inline-flex items-center gap-1.5 rounded-lg bg-brand-500/15 px-3 py-1.5 text-sm font-medium text-brand-500 hover:bg-brand-500/25 dark:text-brand-300">
            <RotateCw className="h-4 w-4" /> Retry
          </button>
        </Card>
      ) : items.length === 0 ? (
        <Card className="flex flex-col items-center gap-2 py-16 text-center">
          <Inbox className="h-10 w-10 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-400">No analyses yet. Analyze an image to see it here.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((it) => {
            const th = scoreTheme(it.quality_score);
            return (
              <Card key={it.id} className="group overflow-hidden">
                <button onClick={() => setOpen(it.id)} className="block w-full text-left">
                  <div className="aspect-video w-full overflow-hidden bg-slate-100 dark:bg-black/30">
                    {it.thumbnail_url
                      ? <img src={it.thumbnail_url} alt={it.filename} className="h-full w-full object-cover transition group-hover:scale-105" />
                      : <div className="flex h-full items-center justify-center text-slate-400">no preview</div>}
                  </div>
                  <div className="p-3">
                    <div className="flex items-center justify-between">
                      <span className="truncate text-sm font-medium">{it.filename}</span>
                      <span className={`text-lg font-bold tabular-nums ${th.text}`}>{it.quality_score}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <Badge className={labelTheme(it.quality_label)}>{titleCase(it.quality_label)}</Badge>
                      {it.primary_issue && <Badge className="text-slate-400 ring-slate-200 dark:ring-white/10">{titleCase(it.primary_issue)}</Badge>}
                      {it.review_recommended && <Badge className="text-amber-300 bg-amber-500/15 ring-amber-500/30">review</Badge>}
                    </div>
                    <p className="mt-2 text-[11px] text-slate-400">{timeAgo(it.created_at)}</p>
                  </div>
                </button>
                <button onClick={() => remove(it.id)}
                  className="flex w-full items-center justify-center gap-1.5 border-t border-slate-200 py-2 text-xs text-slate-400 hover:bg-rose-500/10 hover:text-rose-500 dark:border-white/10">
                  <Trash2 className="h-3.5 w-3.5" /> Delete
                </button>
              </Card>
            );
          })}
        </div>
      )}

      {open && <DetailModal id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

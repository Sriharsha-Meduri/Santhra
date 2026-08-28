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
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/50 p-4 backdrop-blur-sm" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={`Analysis of ${d.filename}`}
        className="my-8 w-full max-w-3xl santhra-fade" onClick={(e) => e.stopPropagation()}>
        <Card className="p-6">
          <div className="mb-4 flex items-start justify-between">
            <div className="flex items-center gap-4">
              <ScoreGauge score={d.quality_score} size={110} />
              <div>
                <p className="font-display text-lg text-ink">{d.filename}</p>
                <p className="text-xs text-muted">{d.image.width}×{d.image.height} · {d.analysis_time_ms} ms</p>
                <div className="mt-2 flex gap-2">
                  <Badge className={labelTheme(d.quality_label)}>{titleCase(d.quality_label)}</Badge>
                  <Badge className={confidenceTheme(d.overall_confidence)}>{d.overall_confidence}</Badge>
                </div>
              </div>
            </div>
            <button onClick={onClose} aria-label="Close" className="rounded-full p-1.5 text-muted hover:bg-paper-2"><X className="h-5 w-5" /></button>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <ImageInspector original={d.thumbnail_url} heatmap={d.heatmap_url} problem={d.problem_regions_url}
              heatmapMethod="Grad-CAM" problemMethod="CV / anomaly" />
            <div><QualityRadar dimensions={d.dimensions} /></div>
          </div>
          <div className="mt-5"><IssueList issues={d.issues} /></div>
          <p className="mt-5 rounded-2xl bg-paper-2 p-4 text-sm text-ink-soft">{d.narrative}</p>
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

  const inputCls = "rounded-full border border-line bg-surface px-3 py-2 text-sm text-ink outline-none transition focus:border-clay";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <span className="eyebrow">Archive</span>
          <h2 className="mt-1 font-display text-3xl text-ink">History <span className="text-muted">({total})</span></h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search filename"
              className={`${inputCls} w-44 pl-9`} />
          </div>
          <select value={label} onChange={(e) => setLabel(e.target.value)} className={inputCls}>
            {LABELS.map((l) => <option key={l} value={l}>{l ? titleCase(l) : "All labels"}</option>)}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value)} className={inputCls}>
            <option value="created_at">Newest</option>
            <option value="quality_score">Score</option>
            <option value="filename">Name</option>
          </select>
        </div>
      </div>

      {stats && stats.total > 0 && !error && (
        <div className="flex flex-wrap gap-8 rounded-[1.4rem] border border-line bg-surface px-6 py-4 text-sm">
          <span className="text-muted">Total analysed <b className="ml-1 font-display text-lg text-ink tabular-nums">{stats.total}</b></span>
          <span className="text-muted">Average score <b className="ml-1 font-display text-lg text-ink tabular-nums">{stats.average_score ?? "-"}</b></span>
          <span className="text-muted">Review rate <b className="ml-1 font-display text-lg text-ink tabular-nums">{Math.round(stats.review_rate * 100)}%</b></span>
        </div>
      )}

      {loading ? (
        <p className="py-16 text-center text-sm text-muted">Loading…</p>
      ) : error ? (
        <Card className="flex flex-col items-center gap-3 py-16 text-center">
          <AlertTriangle className="h-10 w-10 text-ochre" />
          <p className="text-sm text-ink-soft">Could not load history: {error}</p>
          <button onClick={load} className="btn btn-outline px-4 py-2 text-sm"><RotateCw className="h-4 w-4" /> Retry</button>
        </Card>
      ) : items.length === 0 ? (
        <Card className="flex flex-col items-center gap-2 py-16 text-center">
          <Inbox className="h-10 w-10 text-muted/60" />
          <p className="text-sm text-muted">No analyses yet. Analyze an image to see it here.</p>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((it) => {
            const th = scoreTheme(it.quality_score);
            return (
              <Card key={it.id} className="group overflow-hidden">
                <button onClick={() => setOpen(it.id)} className="block w-full text-left">
                  <div className="aspect-video w-full overflow-hidden bg-paper-2">
                    {it.thumbnail_url
                      ? <img src={it.thumbnail_url} alt={it.filename} className="h-full w-full object-cover transition duration-500 group-hover:scale-105" />
                      : <div className="flex h-full items-center justify-center text-muted">no preview</div>}
                  </div>
                  <div className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-ink">{it.filename}</span>
                      <span className={`font-display text-xl tabular-nums ${th.text}`}>{it.quality_score}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-1.5">
                      <Badge className={labelTheme(it.quality_label)}>{titleCase(it.quality_label)}</Badge>
                      {it.primary_issue && <Badge className="text-muted ring-line">{titleCase(it.primary_issue)}</Badge>}
                      {it.review_recommended && <Badge className="text-ochre bg-ochre/12 ring-ochre/25">review</Badge>}
                    </div>
                    <p className="mt-2 eyebrow !text-muted">{timeAgo(it.created_at)}</p>
                  </div>
                </button>
                <button onClick={() => remove(it.id)}
                  className="flex w-full items-center justify-center gap-1.5 border-t border-line py-2.5 text-xs text-muted transition hover:bg-danger/[0.06] hover:text-danger">
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

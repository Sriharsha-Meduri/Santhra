import type {
  AnalysisDetail, AnalysisResult, DemoSample, Health, HistoryList,
  ModelInfo, Statistics,
} from "./types";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch { /* non-json error */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function analyzeFile(file: File | Blob, filename = "upload.jpg"): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file, (file as File).name || filename);
  return handle(await fetch("/api/v1/analyze", { method: "POST", body: form }));
}

export async function listHistory(params: {
  limit?: number; offset?: number; label?: string; search?: string;
  sort?: string; order?: string;
} = {}): Promise<HistoryList> {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v != null && v !== "" && q.set(k, String(v)));
  return handle(await fetch(`/api/v1/analyses?${q.toString()}`));
}

export async function getAnalysis(id: string): Promise<AnalysisDetail> {
  return handle(await fetch(`/api/v1/analyses/${id}`));
}

export async function deleteAnalysis(id: string): Promise<void> {
  const res = await fetch(`/api/v1/analyses/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error("Delete failed");
}

export async function getModelInfo(): Promise<ModelInfo> {
  return handle(await fetch("/api/v1/model/info"));
}

export async function getHealth(): Promise<Health> {
  // /health returns 200 (healthy) or 503 (degraded); both carry the JSON body,
  // so read it directly instead of treating 503 as a thrown error.
  const res = await fetch("/health");
  return res.json() as Promise<Health>;
}

export async function getStatistics(): Promise<Statistics> {
  return handle(await fetch("/api/v1/statistics"));
}

export async function loadDemoSamples(): Promise<DemoSample[]> {
  try {
    const res = await fetch("/samples/samples.json");
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchSampleBlob(url: string): Promise<Blob> {
  return (await fetch(url)).blob();
}

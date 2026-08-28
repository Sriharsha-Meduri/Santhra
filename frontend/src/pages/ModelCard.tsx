import { useEffect, useState } from "react";
import { Cpu, Database, GitBranch, Layers, ShieldCheck } from "lucide-react";
import { getModelInfo } from "../lib/api";
import type { ModelInfo } from "../lib/types";
import { Card, SectionTitle } from "../components/atoms";
import { titleCase } from "../lib/ui";

function Field({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-dashed border-slate-200 py-1.5 dark:border-white/5">
      <span className="text-xs text-slate-500 dark:text-slate-400">{k}</span>
      <span className="text-right text-sm font-medium">{v}</span>
    </div>
  );
}

export function ModelCard() {
  const [m, setM] = useState<ModelInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { getModelInfo().then(setM).catch((e) => setErr(e.message)); }, []);

  if (err) return <p className="text-sm text-rose-400">{err}</p>;
  if (!m) return <p className="py-16 text-center text-sm text-slate-400">Loading…</p>;

  return (
    <div className="space-y-6 santhra-fade">
      <div>
        <h2 className="text-lg font-semibold">Model Card</h2>
        <p className="text-sm text-slate-400">Live metadata from <code>/api/v1/model/info</code></p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle title="Identity & Runtime" />
          <div className="space-y-0.5">
            <Field k="Model" v={m.model_name} />
            <Field k="Version" v={m.model_version} />
            <Field k="Framework" v={m.framework} />
            <Field k="Input resolution" v={`${m.input_resolution}×${m.input_resolution}`} />
            <Field k="Device" v={m.device} />
            <Field k="Pretrained backbone" v={m.pretrained_backbone ? "ImageNet (MobileNetV3-Small)" : "random init"} />
            <Field k="Calibrated" v={m.calibrated ? "yes (temperature scaling)" : "no"} />
            <Field k="Trained at" v={m.trained_at ? new Date(m.trained_at).toLocaleString() : "-"} />
          </div>
        </Card>

        <Card className="p-5">
          <SectionTitle title="Validation Metrics" subtitle="From the held-out validation split" />
          <div className="space-y-0.5">
            {Object.entries(m.validation_metrics).map(([k, v]) => (
              <Field key={k} k={titleCase(k)} v={<span className="tabular-nums">{v}</span>} />
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-400">Full test-set metrics, confusion matrix and failure cases are in <code>docs/evaluation.md</code>.</p>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle title="Architecture & Approach" />
          <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <li className="flex gap-2"><Layers className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" /> Multi-task MobileNetV3-Small: quality-class (3), multi-label issues ({m.issue_types.length}), 0-100 score regression.</li>
            <li className="flex gap-2"><Cpu className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" /> A separate conv-autoencoder learns the clean-image distribution for anomaly detection.</li>
            <li className="flex gap-2"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" /> Fused with a classical CV feature engine; both opinions are surfaced and reconciled.</li>
            <li className="flex gap-2"><GitBranch className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" /> Loss weights: {JSON.stringify(m.loss_weights)}.</li>
          </ul>
        </Card>

        <Card className="p-5">
          <SectionTitle title="Data & Labels" />
          <p className="flex gap-2 text-sm text-slate-600 dark:text-slate-300">
            <Database className="mt-0.5 h-4 w-4 shrink-0 text-brand-400" />
            Trained on deterministic, seeded degradations of natural images (Imagenette). Sources are
            split <b>before</b> degradation to prevent leakage.
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {m.issue_types.map((i) => (
              <span key={i} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600 dark:bg-white/5 dark:text-slate-300">{titleCase(i)}</span>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <SectionTitle title="Intended use & limitations" />
        <div className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="font-semibold text-emerald-500 dark:text-emerald-300">Intended</p>
            <p className="text-slate-600 dark:text-slate-300">Automated first-pass screening of image technical quality (blur, exposure, noise, contrast, compression, colour) with explainable evidence.</p>
          </div>
          <div>
            <p className="font-semibold text-rose-500 dark:text-rose-300">Not intended</p>
            <p className="text-slate-600 dark:text-slate-300">Confirming physical product defects, medical/forensic decisions, or detecting arbitrary real-world defect types. The anomaly signal is an <i>uncalibrated score</i>, not a confirmed defect.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

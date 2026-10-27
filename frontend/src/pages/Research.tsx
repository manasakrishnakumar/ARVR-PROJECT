import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ErrorBar, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../services/api";
import type { ResearchResult } from "../types/api";

const NAMES: Record<string, string> = {
  majority_class: "Majority class", rule_based: "Rule-based (illustrative thresholds)", rule_range_tuned: "Range rule (tuned)",
  rf_base: "Forest, angles", rf_base_tuned: "Forest, angles (tuned)", rf_posture: "Forest, + posture", rf_posture_tuned: "Forest, + posture (tuned)",
  random_forest: "Random forest",
};
const pretty = (k: string) => NAMES[k] ?? k.replace(/_/g, " ");
const f3 = (x: number | null | undefined) => (typeof x === "number" && Number.isFinite(x) ? x.toFixed(3) : "n/a");

function ExternalView({ d }: { d: any }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const rows = Object.entries<any>(d.methods).map(([k, m]) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const [lo, hi] = m.balanced_accuracy_ci95_participant_bootstrap;
    return { name: k.replace(/ \(.*\)/, "").replace(/_/g, " "), full: k, bal: m.balanced_accuracy, err: [m.balanced_accuracy - lo, hi - m.balanced_accuracy], m };
  });
  const ref = d.in_domain_reference_loo_participant as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <>
      <p className="muted">
        Test set: {d.n_test} repetitions from {d.test_participants.length} people; trained on {d.n_train} repetitions from {d.train_participants.length} people.
        Exercises: {d.shared_exercises.join(", ")}. {(d.test_incorrect_fraction * 100).toFixed(0)}% of test repetitions are incorrect, so guessing "correct" every time scores 0.5 balanced accuracy.
      </p>
      <div className="chart-box" role="img" aria-label="Balanced accuracy per method with 95 percent confidence intervals">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 24, left: -8 }}>
            <CartesianGrid stroke="var(--grid)" strokeDasharray="3 3" />
            <XAxis dataKey="name" stroke="var(--muted)" fontSize={11} interval={0} angle={-12} textAnchor="end" height={50} />
            <YAxis domain={[0.3, 0.85]} stroke="var(--muted)" fontSize={12} />
            <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--grid)", color: "var(--text)" }} formatter={(v) => (typeof v === "number" ? v.toFixed(3) : String(v ?? ""))} />
            <Bar dataKey="bal" name="Balanced accuracy" fill="var(--c1)" isAnimationActive={false}>
              <ErrorBar dataKey="err" stroke="var(--text)" width={5} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>Method</th><th>Balanced acc.</th><th>95% CI</th><th>Accuracy</th><th>Incorrect: precision</th><th>recall</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.full}><td>{r.full}</td><td>{f3(r.bal)}</td>
                <td>{f3(r.bal - r.err[0])} to {f3(r.bal + r.err[1])}</td><td>{f3(r.m.accuracy)}</td>
                <td>{f3(r.m.incorrect_precision)}</td><td>{f3(r.m.incorrect_recall)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <h4>Reference: trained and tested inside the test dataset (leave one person out)</h4>
      <ul>{Object.entries(ref).map(([k, m]) => <li key={k}>{k.replace(/_/g, " ")}: balanced accuracy {f3(m.balanced_accuracy)}</li>)}</ul>
    </>
  );
}

function MethodsView({ d, kind }: { d: any; kind: string }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const methods: Record<string, any> = kind === "lopo" ? d.methods : Object.fromEntries(["majority_class", "rule_based", "random_forest"].map((k) => [k, d[k]])); // eslint-disable-line @typescript-eslint/no-explicit-any
  const sizes = kind === "lopo" ? `${d.n} repetitions, ${d.participants.length} participants (${d.participants.join(", ")})` : `${d._sizes.train_rows} train / ${d._sizes.test_rows} test repetitions, ${d._sizes.train_participants} / ${d._sizes.test_participants} participants`;
  return (
    <>
      <p className="muted">{sizes}.</p>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>Method</th><th>Accuracy</th><th>Macro-F1</th><th>Macro-F1 95% CI</th>{kind === "lopo" && <th>Binary balanced acc.</th>}</tr></thead>
          <tbody>
            {Object.entries(methods).map(([k, m]) => {
              const ci = m.macro_f1_ci95_participant_bootstrap;
              return (
                <tr key={k}><td>{pretty(k)}</td><td>{f3(m.accuracy)}</td><td>{f3(m.macro_f1)}</td>
                  <td>{ci ? `${f3(ci[0])} to ${f3(ci[1])}` : "n/a"}</td>
                  {kind === "lopo" && <td>{f3(m.binary_correct_vs_incorrect?.balanced_accuracy)}</td>}</tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function Research() {
  const [res, setRes] = useState<ResearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.researchResults().then((r) => setRes(r.results)).catch((e: Error) => setError(e.message)); }, []);

  return (
    <>
      <h1>Research evaluation</h1>
      <p className="notice">
        These are the project's own evaluation results, computed by its scripts from public research datasets (REHAB26-ViewAngles and REHAB24-6, CC BY-NC 4.0)
        and a synthetic pipeline check. They are preliminary, based on few healthy volunteers who performed deliberate errors, and are not clinical evidence.
        Nothing here shows that the system, or adaptive difficulty, improves recovery.
      </p>
      {error && <p className="error" role="alert">Could not load results: {error}</p>}
      {!error && res === null && <p className="muted">Loading results...</p>}
      {res && res.length === 0 && <p className="muted">No result files found. Generate them with the evaluation scripts (see docs).</p>}
      {res?.map((r) => (
        <section className="card" key={r.id}>
          <h2>{r.title}</h2>
          {r.kind === "synthetic" && <p className="notice error-banner"><strong>SYNTHETIC DATA ONLY.</strong> Labels come from a generator, not from people. This proves the pipeline runs; it says nothing about real-world accuracy.</p>}
          <p className="muted">{r.caveat}</p>
          {r.kind === "external" ? <ExternalView d={r.data} /> : <MethodsView d={r.data} kind={r.kind} />}
        </section>
      ))}
      <section className="card">
        <h2>How to read these numbers</h2>
        <ul>
          <li><strong>Balanced accuracy</strong> averages recall on correct and incorrect repetitions; 0.5 is chance.</li>
          <li><strong>Confidence intervals</strong> resample whole participants, because repetitions from one person are not independent. With only a handful of people they are wide.</li>
          <li><strong>Leave-one-participant-out</strong> trains on every person but one and tests on the one left out, repeating for each person.</li>
          <li><strong>External validation</strong> trains on one dataset and tests on a different one (different people, cameras, setting) with nothing tuned on the test data.</li>
        </ul>
      </section>
    </>
  );
}

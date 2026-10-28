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
    const short = k.replace(" (trained on train set)", "").replace(" (threshold chosen on train participants)", " + train threshold")
      .replace(" (train prior)", "").replace(" (threshold from train)", "").replace(/^rf_/, "forest ").replace(/_/g, " ");
    return { name: short, full: k, bal: m.balanced_accuracy, err: [m.balanced_accuracy - lo, hi - m.balanced_accuracy], m };
  });
  const cal = d.probability_calibration_on_test as Record<string, any> | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
  const thr = d.decision_thresholds_from_train as Record<string, number> | undefined;
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
      {thr && cal && (
        <>
          <h4>Decision threshold and probability calibration</h4>
          <p className="muted">
            The threshold on the predicted probability of "incorrect" was chosen using only the training dataset (out-of-fold predictions from
            leave-one-participant-out), never the test data. "Threshold chosen on train participants" rows above use it. The raw probabilities are
            not well calibrated on the new dataset (mean predicted probability far above the observed rate), so they should not be shown to users as likelihoods.
          </p>
          <div className="table-wrap">
            <table className="angles">
              <thead><tr><th>Features</th><th>Train-chosen threshold</th><th>Brier</th><th>ECE</th><th>Mean predicted</th><th>Observed rate</th></tr></thead>
              <tbody>
                {Object.keys(cal).map((k) => (
                  <tr key={k}><td>{k.replace(/_/g, " ")}</td><td>{thr[k]?.toFixed(2)}</td><td>{f3(cal[k].brier)}</td><td>{f3(cal[k].ece)}</td>
                    <td>{f3(cal[k].mean_predicted_probability)}</td><td>{f3(cal[k].observed_incorrect_rate)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
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

function CountingView({ d }: { d: any }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <>
      <p className="muted">
        Detected repetitions are matched to the dataset's labelled repetition boundaries (overlap of at least 50%). "Illustrative" uses the exercise
        definition's angles; "auto" calibrates each recording's range from its own angle trace (10th to 90th percentile; no labels used).
      </p>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>Dataset</th><th>Range setting</th><th>Labelled</th><th>Detected</th><th>Mean count error</th><th>Exactly right</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
          <tbody>
            {Object.entries<any>(d).flatMap(([ds, modes]) => Object.entries<any>(modes).map(([mode, m]) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
              <tr key={ds + mode}><td>{ds}</td><td>{mode}</td><td>{m.labelled_repetitions}</td><td>{m.detected_repetitions}</td>
                <td>{f3(m.mean_absolute_count_error)}</td><td>{f3(m.exact_count_fraction)}</td><td>{f3(m.precision)}</td><td>{f3(m.recall)}</td><td>{f3(m.f1)}</td></tr>
            )))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function AngleView({ d }: { d: any }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const rows: [string, any][] = [["All", d.overall], ...Object.entries<any>(d.by_exercise), ...Object.entries<any>(d.by_camera)]; // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <>
      <p className="muted">{d.recordings} recordings. Median best-agreement frame lag: {d.best_lag_frames_median} (0 means the two sources are frame-aligned).</p>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>Subset</th><th>Frames</th><th>MAE (°)</th><th>RMSE (°)</th><th>Bias (°)</th><th>95% limits of agreement (°)</th><th>Correlation r</th></tr></thead>
          <tbody>
            {rows.map(([k, m]) => (
              <tr key={k}><td>{k.replace("_", " ")}</td><td>{m.n}</td><td>{f3(m.mae_deg)}</td><td>{f3(m.rmse_deg)}</td><td>{f3(m.bias_deg)}</td>
                <td>{m.loa95_deg ? `${m.loa95_deg[0].toFixed(1)} to ${m.loa95_deg[1].toFixed(1)}` : "n/a"}</td><td>{f3(m.pearson_r)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">{d.note}</p>
    </>
  );
}

function PerformanceView({ d }: { d: any }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  const rows: [string, any][] = [["Analysis cost per angle sample", d.analysis_cost_per_sample], ["WebSocket round trip (in-process)", d.websocket_round_trip]]; // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>Measurement</th><th>Samples</th><th>Mean (ms)</th><th>95th pct (ms)</th><th>99th pct (ms)</th><th>Max (ms)</th></tr></thead>
          <tbody>{rows.map(([name, m]) => (
            <tr key={name}><td>{name}</td><td>{m.samples ?? m.messages}</td><td>{m.mean_ms.toFixed(3)}</td><td>{m.p95_ms.toFixed(3)}</td><td>{m.p99_ms.toFixed(3)}</td><td>{m.max_ms.toFixed(3)}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <p className="muted">The browser sends one angle about every {d.budget.sample_interval_ms} ms; the 99th-percentile round trip is {d.within_budget ? "well inside" : "NOT inside"} that interval. Browser pose-estimation speed is not included.</p>
    </>
  );
}

function SimulationView({ d }: { d: any }) { // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <>
      <p className="notice error-banner"><strong>SIMULATION.</strong> Made-up user models with stated assumptions ({d.n_users_per_model} simulated users per model, {d.n_sessions} sessions each).
        This checks how the controller behaves; it does not show that adaptive difficulty helps real people.</p>
      <div className="table-wrap">
        <table className="angles">
          <thead><tr><th>User model</th><th>Policy</th><th>Too hard</th><th>Too easy</th><th>Mismatch</th><th>Level changes</th><th>Reversals</th><th>Pause suggested</th></tr></thead>
          <tbody>
            {Object.entries<any>(d.models).flatMap(([model, v]) => Object.entries<any>(v.policies).map(([pol, m]) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
              <tr key={model + pol} style={pol === "adaptive" ? { fontWeight: 600 } : undefined}>
                <td>{model}</td><td>{pol.replace(/_/g, " ")}</td><td>{f3(m.too_hard_share)}</td><td>{f3(m.too_easy_share)}</td><td>{f3(m.mismatch_share)}</td>
                <td>{m.level_changes.toFixed(1)}</td><td>{m.direction_reversals.toFixed(1)}</td><td>{f3(m.pause_share)}</td></tr>
            )))}
          </tbody>
        </table>
      </div>
      <ul>
        {Object.entries<any>(d.models).map(([model, v]) => ( // eslint-disable-line @typescript-eslint/no-explicit-any
          <li key={model}>{model}: adaptive minus best fixed ({v.best_fixed_by_mismatch.replace(/_/g, " ")}) mismatch share {v.adaptive_minus_best_fixed_mismatch_share.mean.toFixed(2)}
            {" "}(95% CI {v.adaptive_minus_best_fixed_mismatch_share.ci95[0].toFixed(2)} to {v.adaptive_minus_best_fixed_mismatch_share.ci95[1].toFixed(2)}); safety violations: {v.safety_violations_total}</li>
        ))}
      </ul>
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
        These are the project's own evaluation results, computed by its scripts from public research datasets (REHAB26-ViewAngles and REHAB24-6, CC BY-NC 4.0),
        a synthetic pipeline check, and a clearly labelled simulation of the adaptive controller. They are preliminary, based on few healthy volunteers who performed deliberate errors, and are not clinical evidence.
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
          {r.kind === "external" ? <ExternalView d={r.data} />
            : r.kind === "counting" ? <CountingView d={r.data} />
            : r.kind === "angle" ? <AngleView d={r.data} />
            : r.kind === "simulation" ? <SimulationView d={r.data} />
            : r.kind === "performance" ? <PerformanceView d={r.data} />
            : <MethodsView d={r.data} kind={r.kind} />}
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

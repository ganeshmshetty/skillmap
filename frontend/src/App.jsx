import { useState, useCallback } from "react";
import "./styles.css";

// Expose React globally so sub-components can call window.React.useState
// (they import hooks this way to keep imports clean in simpler files)
import React from "react";
window.React = React;

import UploadPanel from "./UploadPanel";
import ProgressBar from "./ProgressBar";
import SummaryCards from "./SummaryCards";
import SkillGapHeatmap from "./SkillGapHeatmap";
import PathwayFlowGraph from "./PathwayFlowGraph";
import ReasoningPanel from "./ReasoningPanel";
import { BrainCircuit } from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Step key constants
const STEPS = { UPLOAD: 0, PROCESSING: 1, RESULTS: 2 };

const STEP_META = [
  { label: "Upload" },
  { label: "Analyzing" },
  { label: "Results" },
];

/* ---- Step Indicator ---- */
function StepIndicator({ current }) {
  return (
    <div className="step-indicator">
      {STEP_META.map((s, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <React.Fragment key={s.label}>
            <div
              className={`step-dot${active ? " active" : ""}${done ? " done" : ""}`}
            >
              <div className="step-circle">{done ? "✓" : i + 1}</div>
              <span style={{ whiteSpace: "nowrap" }}>{s.label}</span>
            </div>
            {i < STEP_META.length - 1 && (
              <div className={`step-line${done ? " done" : ""}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ---- Main App ---- */
export default function App() {
  const [step, setStep] = useState(STEPS.UPLOAD);
  const [jobId, setJobId] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);

  /* ---- Upload handler ---- */
  async function handleSubmit({ resume, jd }) {
    setError(null);
    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("jd", jd);

    let res;
    try {
      res = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        body: formData,
      });
    } catch {
      setError("Cannot reach the server. Is the API running?");
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      setError(err?.error?.message || "Upload failed.");
      return;
    }

    const data = await res.json();
    setJobId(data.job_id);
    setStep(STEPS.PROCESSING);
  }

  /* ---- Poll complete ---- */
  const handleComplete = useCallback((data) => {
    setResult(data.result);
    setStep(STEPS.RESULTS);
  }, []);

  /* ---- Poll error ---- */
  const handlePollError = useCallback((msg) => {
    setError(msg);
    setStep(STEPS.UPLOAD);
  }, []);

  /* ---- Reset ---- */
  function handleReset() {
    setStep(STEPS.UPLOAD);
    setJobId(null);
    setResult(null);
    setError(null);
    setSelectedModule(null);
  }

  /* ---- module select for reasoning panel ---- */
  const handleSelectModule = useCallback((mod) => {
    setSelectedModule(mod);
  }, []);

  return (
    <>
      {/* Animated background */}
      <div className="mesh-bg" />

      <div className="page">
        {/* ---- Header ---- */}
        <header className="header">
          <div className="header-logo"><BrainCircuit size={20} strokeWidth={2.5} color="var(--on-surface)" /></div>
          <div className="header-title">AI-Adaptive Onboarding Engine</div>
          <div className="header-badge">Hackathon 2026</div>
        </header>

        {/* ---- Main ---- */}
        <main className="main-content">
          <StepIndicator current={step} />

          {/* UPLOAD */}
          {step === STEPS.UPLOAD && (
            <div className="glass-card" style={{ animation: "slideUp 0.4s ease" }}>
              <UploadPanel onSubmit={handleSubmit} error={error} />
            </div>
          )}

          {/* PROCESSING */}
          {step === STEPS.PROCESSING && (
            <ProgressBar
              jobId={jobId}
              apiBase={API_BASE_URL}
              onComplete={handleComplete}
              onError={handlePollError}
            />
          )}

          {/* RESULTS */}
          {step === STEPS.RESULTS && result && (
            <div style={{ animation: "slideUp 0.4s ease" }}>
              <div className="results-header">
                <div>
                  <h1 className="section-title">Your Learning Pathway</h1>
                  <p className="section-subtitle">
                    {result.pathway?.nodes?.length || 0} personalized modules ·
                    grounded, hallucination-free recommendations
                  </p>
                </div>
                <button
                  id="reset-btn"
                  className="btn-reset"
                  onClick={handleReset}
                >
                  ← New Analysis
                </button>
              </div>

              {/* Metric Cards */}
              <SummaryCards result={result} />

              {/* Skill Gap Chart */}
              <SkillGapHeatmap gapVector={result.gap_vector || buildGapFromPathway(result)} />

              {/* React Flow DAG */}
              <PathwayFlowGraph
                pathway={result.pathway}
                onSelectModule={handleSelectModule}
              />
            </div>
          )}
        </main>
      </div>

      {/* Reasoning Side Panel */}
      {selectedModule && (
        <ReasoningPanel
          module={selectedModule}
          traces={result?.reasoning_traces}
          onClose={() => setSelectedModule(null)}
        />
      )}
    </>
  );
}

/**
 * Derive a gap vector from pathway nodes when the API doesn't return one explicitly.
 * Uses node reasoning confidence as a proxy for gap size.
 */
function buildGapFromPathway(result) {
  const nodes = result?.pathway?.nodes || [];

  return nodes.map((n) => {
    const trace = n.reasoning || result?.reasoning_traces?.find((t) => t.module_id === n.module_id);
    const conf = trace?.confidence ?? 0.7;
    return {
      skill_name: n.skill_gaps_covered?.[0] || n.title,
      onet_id: n.module_id,
      gap_score: 1 - conf,
      importance: conf,
    };
  });
}

import { useState, useEffect, useRef } from "react";

const STEPS = [
    { icon: "📤", label: "Uploading" },
    { icon: "🔍", label: "Parsing Skills" },
    { icon: "📊", label: "Computing Gaps" },
    { icon: "🧭", label: "Building Pathway" },
];

// Map API status to step index (0-based)
function statusToStep(status) {
    if (status === "queued") return 0;
    if (status === "processing") return 2;
    if (status === "completed") return 3;
    return 0;
}

export default function ProgressBar({ jobId, apiBase, onComplete, onError }) {
    const [currentStep, setCurrentStep] = useState(0);
    const [apiStatus, setApiStatus] = useState("queued");
    const intervalRef = useRef(null);

    useEffect(() => {
        if (!jobId) return;

        // Animate step 1 immediately
        setCurrentStep(1);

        intervalRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${apiBase}/result/${jobId}`);
                if (!res.ok) throw new Error("Fetch failed");
                const data = await res.json();
                setApiStatus(data.status);
                setCurrentStep(statusToStep(data.status));

                if (data.status === "completed") {
                    clearInterval(intervalRef.current);
                    setTimeout(() => onComplete(data), 600);
                } else if (data.status === "failed") {
                    clearInterval(intervalRef.current);
                    onError(data.error?.message || "Analysis failed.");
                }
            } catch (err) {
                clearInterval(intervalRef.current);
                onError("Could not reach the server.");
            }
        }, 1500);

        return () => clearInterval(intervalRef.current);
    }, [jobId, apiBase, onComplete, onError]);

    const progress = ((currentStep + 1) / STEPS.length) * 100;

    return (
        <div className="glass-card progress-card">
            <div className="progress-title">Analyzing your profile…</div>
            <div className="progress-subtitle">
                Our AI is parsing skills, computing gaps, and building your personalized pathway.
            </div>

            <div className="progress-steps">
                {STEPS.map((step, i) => {
                    const done = i < currentStep;
                    const active = i === currentStep;
                    return (
                        <div key={step.label} style={{ display: "flex", alignItems: "center" }}>
                            <div className="ps-item">
                                <div className={`ps-dot${active ? " active" : ""}${done ? " done" : ""}`}>
                                    {done ? "✓" : step.icon}
                                </div>
                                <div className={`ps-label${active ? " active" : ""}${done ? " done" : ""}`}>
                                    {step.label}
                                </div>
                            </div>
                            {i < STEPS.length - 1 && (
                                <div className={`ps-connector${done ? " done" : ""}`} />
                            )}
                        </div>
                    );
                })}
            </div>

            <div className="progress-track">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>

            <p style={{ marginTop: 16, fontSize: 12, color: "var(--text-muted)" }}>
                Job ID: <code style={{ color: "var(--text-secondary)" }}>{jobId}</code>
                &nbsp;·&nbsp;Status: <span style={{ color: "var(--accent-blue)" }}>{apiStatus}</span>
            </p>
        </div>
    );
}

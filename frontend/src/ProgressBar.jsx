import { useState, useEffect, useRef } from "react";
import { UploadCloud, Search, BarChart2, Compass, Check } from "lucide-react";
import LiveFeed from "./LiveFeed";

const STEPS = [
    { icon: <UploadCloud size={20} strokeWidth={2.5} />, label: "Uploading" },
    { icon: <Search size={20} strokeWidth={2.5} />, label: "Parsing Skills" },
    { icon: <BarChart2 size={20} strokeWidth={2.5} />, label: "Computing Gaps" },
    { icon: <Compass size={20} strokeWidth={2.5} />, label: "Building Pathway" },
];

// Map API status to step index (0-based)
function statusToStep(status) {
    const s = status?.toLowerCase();
    if (s === "queued") return 0;
    if (s === "processing") return 2;
    if (s === "completed" || s === "complete" || s === "done") return 3;
    return 0;
}

export default function ProgressBar({ jobId, apiBase, onComplete, onError }) {
    const [currentStep, setCurrentStep] = useState(0);
    const [apiStatus, setApiStatus] = useState("queued");
    const [events, setEvents] = useState([]);
    
    const intervalRef = useRef(null);
    const eventCursor = useRef(0);

    useEffect(() => {
        if (!jobId) return;

        // Animate step 1 immediately
        setCurrentStep(1);

        intervalRef.current = setInterval(async () => {
            try {
                const res = await fetch(`${apiBase}/result/${jobId}?since=${eventCursor.current}`);
                if (!res.ok) throw new Error("Fetch failed");
                const data = await res.json();
                
                setApiStatus(data.status);
                setCurrentStep(statusToStep(data.status));
                
                if (data.events && data.events.length > 0) {
                    setEvents(prev => [...prev, ...data.events]);
                    eventCursor.current = data.event_count;
                }

                if (data.status === "completed" || data.status === "complete") {
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
        <div className="glass-card progress-card" style={{ maxWidth: 1000, margin: "0 auto" }}>
            <div className="progress-title">Analyzing your profile...</div>
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
                                    {done ? <Check size={20} strokeWidth={3} /> : step.icon}
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
            
            <LiveFeed events={events} />

            <p style={{ marginTop: 16, fontSize: 12, color: "var(--text-muted)", textAlign: "center" }}>
                Job ID: <code style={{ color: "var(--text-secondary)" }}>{jobId}</code>
                &nbsp;·&nbsp;Status: <span style={{ color: "var(--accent-blue)" }}>{apiStatus}</span>
            </p>
        </div>
    );
}

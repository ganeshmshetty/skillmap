import { useState, useEffect, useRef } from "react";
import { Target, Scissors, Clock } from "lucide-react";

function useCountUp(target, duration = 1200) {
    const [value, setValue] = useState(0);
    useEffect(() => {
        let start = 0;
        const targetNum = Number(target) || 0;
        const step = targetNum / (duration / 16);
        const timer = setInterval(() => {
            start += step;
            if (start >= targetNum) { setValue(targetNum); clearInterval(timer); }
            else setValue(Math.round(start * 100) / 100);
        }, 16);
        return () => clearInterval(timer);
    }, [target, duration]);
    return value;
}

function MetricCard({ icon, label, value, formatted, color, delay = 0, tooltip }) {
    return (
        <div className="metric-card" style={{ animationDelay: `${delay}ms` }} title={tooltip}>
            <span className="metric-icon">{icon}</span>
            <div className="metric-value" style={{ color }}>
                {formatted}
            </div>
            <div className="metric-label">{label}</div>
        </div>
    );
}

export default function SummaryCards({ result }) {
    const coverage = useCountUp(
        (result?.coverage_score ?? 0) * 100,
        1000
    );
    const redundancy = useCountUp(
        (result?.redundancy_reduction ?? 0) * 100,
        1000
    );
    const minutes = useCountUp(result?.pathway?.total_duration ?? 0, 1200);
    const hours = Math.round((minutes / 60) * 10) / 10;

    // Format to max 2 decimal places, strip trailing zeros
    const fmt = (v) => parseFloat(v.toFixed(2));

    return (
        <div className="summary-grid">
            <MetricCard
                icon={<Target size={32} strokeWidth={2.5} />}
                label="Coverage Score"
                value={coverage}
                formatted={`${fmt(coverage)}%`}
                color="var(--accent-teal)"
                delay={0}
                tooltip="Percentage of job requirements covered by your current skills. 100% means you meet all core requirements."
            />
            <MetricCard
                icon={<Scissors size={32} strokeWidth={2.5} />}
                label="Redundancy Reduction"
                value={redundancy}
                formatted={`${fmt(redundancy)}%`}
                color="var(--accent-blue)"
                delay={100}
                tooltip="Time saved by skipping modules for skills you already know. 0% means you are taking the full static curriculum."
            />
            <MetricCard
                icon={<Clock size={32} strokeWidth={2.5} />}
                label="Estimated Pathway Time"
                formatted={`${hours}h`}
                color="var(--accent-teal)"
                delay={200}
                tooltip="Total estimated time to complete all missing skill modules in the adaptive pathway."
            />
            <MetricCard
                icon={<Target size={32} strokeWidth={2.5} />}
                label="Target Domain"
                formatted={result?.detected_domain || "General"}
                color="var(--surface)"
                delay={300}
                tooltip="The primary career domain identified from the provided Job Description."
            />
        </div>
    );
}

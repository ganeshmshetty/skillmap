import { useState, useEffect, useRef } from "react";

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

function MetricCard({ icon, label, value, formatted, color, delay = 0 }) {
    return (
        <div className="metric-card" style={{ animationDelay: `${delay}ms` }}>
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
        Math.round((result?.coverage_score ?? 0) * 100),
        1000
    );
    const redundancy = useCountUp(
        Math.round((result?.redundancy_reduction ?? 0) * 100),
        1000
    );
    const minutes = useCountUp(result?.pathway?.total_duration ?? 0, 1200);
    const hours = Math.round((minutes / 60) * 10) / 10;

    return (
        <div className="summary-grid">
            <MetricCard
                icon="🎯"
                label="Coverage Score"
                value={coverage}
                formatted={`${coverage}%`}
                color="var(--accent-teal)"
                delay={0}
            />
            <MetricCard
                icon="✂️"
                label="Redundancy Reduction"
                value={redundancy}
                formatted={`${redundancy}%`}
                color="var(--accent-blue)"
                delay={100}
            />
            <MetricCard
                icon="⏱️"
                label="Estimated Pathway Time"
                formatted={`${hours}h`}
                color="var(--accent-amber)"
                delay={200}
            />
        </div>
    );
}

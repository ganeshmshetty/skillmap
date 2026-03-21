import { useEffect, useRef } from "react";
import { Target, Scissors, Clock } from "lucide-react";

function useCountUp(target, duration = 1200) {
    const [value, setValue] = window.React.useState(0);
    useEffect(() => {
        let start = 0;
        const step = target / (duration / 16);
        const timer = setInterval(() => {
            start += step;
            if (start >= target) { setValue(target); clearInterval(timer); }
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
                icon={<Target size={32} strokeWidth={2.5} />}
                label="Coverage Score"
                value={coverage}
                formatted={`${coverage}%`}
                color="var(--accent-teal)"
                delay={0}
            />
            <MetricCard
                icon={<Scissors size={32} strokeWidth={2.5} />}
                label="Redundancy Reduction"
                value={redundancy}
                formatted={`${redundancy}%`}
                color="var(--accent-blue)"
                delay={100}
            />
            <MetricCard
                icon={<Clock size={32} strokeWidth={2.5} />}
                label="Estimated Pathway Time"
                formatted={`${hours}h`}
                color="var(--accent-amber)"
                delay={200}
            />
        </div>
    );
}

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from "recharts";

function gapColor(score) {
    if (score >= 0.7) return "var(--accent-coral)";
    if (score >= 0.4) return "var(--accent-amber)";
    return "var(--accent-teal)";
}

const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
        <div
            style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 13,
            }}
        >
            <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--text-primary)" }}>
                {d.name}
            </div>
            <div style={{ color: "var(--text-secondary)" }}>
                Gap Score:{" "}
                <span style={{ color: gapColor(d.gap), fontWeight: 700 }}>
                    {Math.round(d.gap * 100)}%
                </span>
            </div>
            {d.importance && (
                <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 2 }}>
                    O*NET Importance: {Math.round(d.importance * 100)}
                </div>
            )}
        </div>
    );
};

export default function SkillGapHeatmap({ gapVector }) {
    if (!gapVector || gapVector.length === 0) return null;

    const data = gapVector.slice(0, 12).map((g) => ({
        name: g.skill_name || g.onet_id || "Unknown Skill",
        gap: Math.min(
            1,
            Math.max(
                0,
                g.gap_score ??
                (typeof g.required_level === "number" && typeof g.current_level === "number"
                    ? Math.max(0, g.required_level - g.current_level) / 3
                    : 0.5)
            )
        ),
        importance: g.importance,
    }));

    return (
        <div className="glass-card chart-card">
            <div className="chart-title">
                📊 Skill Gap Analysis
                <span
                    style={{
                        fontSize: 11,
                        fontWeight: 500,
                        color: "var(--text-muted)",
                        marginLeft: "auto",
                    }}
                >
                    Higher bar = larger gap
                </span>
            </div>

            <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
                {[
                    { color: "var(--accent-coral)", label: "Large gap (>70%)" },
                    { color: "var(--accent-amber)", label: "Medium gap (40–70%)" },
                    { color: "var(--accent-teal)", label: "Small gap (<40%)" },
                ].map((l) => (
                    <div
                        key={l.label}
                        style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}
                    >
                        <span
                            style={{
                                width: 10,
                                height: 10,
                                borderRadius: 3,
                                background: l.color,
                                display: "inline-block",
                            }}
                        />
                        <span style={{ color: "var(--text-secondary)" }}>{l.label}</span>
                    </div>
                ))}
            </div>

            <ResponsiveContainer width="100%" height={280}>
                <BarChart
                    data={data}
                    layout="vertical"
                    margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
                >
                    <CartesianGrid
                        horizontal={false}
                        stroke="rgba(255,255,255,0.05)"
                    />
                    <XAxis
                        type="number"
                        domain={[0, 1]}
                        tickFormatter={(v) => `${Math.round(v * 100)}%`}
                        tick={{ fill: "var(--text-muted)", fontSize: 11 }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={false}
                    />
                    <YAxis
                        type="category"
                        dataKey="name"
                        width={140}
                        tick={{ fill: "var(--text-secondary)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
                    <Bar dataKey="gap" radius={[0, 4, 4, 0]} maxBarSize={18}>
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={gapColor(entry.gap)} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

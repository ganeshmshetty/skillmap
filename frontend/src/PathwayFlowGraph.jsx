import { useCallback, useMemo } from "react";
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import { Map } from "lucide-react";

/* ---- Phase config ---- */
const PHASE_CONFIG = {
    Foundation: { badgeClass: "foundation", color: "#3b82f6" },
    Core: { badgeClass: "core", color: "#a855f7" },
    Advanced: { badgeClass: "advanced", color: "#f87171" },
};

/* ---- Custom Node ---- */
function PathwayNode({ data, selected }) {
    const cfg = PHASE_CONFIG[data.phase] || PHASE_CONFIG.Foundation;
    return (
        <div
            id={`node-${data.module_id}`}
            className={`rf-node phase-${data.phase?.toLowerCase()}${selected ? " selected" : ""}`}
            onClick={() => data.onSelect && data.onSelect(data)}
        >
            <div className={`rf-node-badge ${cfg.badgeClass}`}>{data.phase}</div>
            <div className="rf-node-title">{data.title}</div>
            <div className="rf-node-id">{data.module_id}</div>
        </div>
    );
}

const NODE_TYPES = { pathway: PathwayNode };

/* ---- Layout: simple left-to-right layered layout ---- */
function buildLayout(nodes, edges) {
    // Group by phase order
    const PHASE_ORDER = ["Foundation", "Core", "Advanced"];
    const groups = {};
    PHASE_ORDER.forEach((p) => { groups[p] = []; });

    nodes.forEach((n) => {
        const phase = n.phase || "Foundation";
        if (!groups[phase]) groups[phase] = [];
        groups[phase].push(n);
    });

    const rfNodes = [];
    let col = 0;
    PHASE_ORDER.forEach((phase) => {
        const group = groups[phase];
        group.forEach((n, row) => {
            rfNodes.push({
                id: n.module_id,
                type: "pathway",
                position: { x: col * 240, y: row * 140 },
                data: n,
            });
        });
        if (group.length > 0) col++;
    });

    const fallbackEdges = [];
    if ((!edges || edges.length === 0) && rfNodes.length > 1) {
        for (let i = 0; i < rfNodes.length - 1; i += 1) {
            fallbackEdges.push({
                from: rfNodes[i].id,
                to: rfNodes[i + 1].id,
                type: "sequence",
            });
        }
    }

    const sourceEdges = edges && edges.length > 0 ? edges : fallbackEdges;

    const rfEdges = sourceEdges.map((e, i) => ({
        id: `e-${e.from}-${e.to}-${i}`,
        source: e.from,
        target: e.to,
        label: e.type || "",
        style: { stroke: "rgba(110,118,255,0.5)", strokeWidth: 1.5 },
        labelStyle: { fill: "rgba(139,143,168,0.8)", fontSize: 10 },
        animated: true,
    }));

    return { rfNodes, rfEdges };
}

export default function PathwayFlowGraph({ pathway, onSelectModule }) {
    const rawNodes = pathway?.nodes || [];
    const rawEdges = pathway?.edges || [];

    const { rfNodes: initialNodes, rfEdges: initialEdges } = useMemo(
        () => buildLayout(rawNodes, rawEdges),
        [rawNodes, rawEdges]
    );

    // Inject the onSelect callback into each node's data
    const nodesWithCallback = useMemo(
        () =>
            initialNodes.map((n) => ({
                ...n,
                data: { ...n.data, onSelect: onSelectModule },
            })),
        [initialNodes, onSelectModule]
    );

    const [nodes, , onNodesChange] = useNodesState(nodesWithCallback);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);

    if (rawNodes.length === 0) return null;

    return (
        <div className="glass-card flow-card">
            <div className="flow-header">
                <div className="flow-header-title"><Map size={24} strokeWidth={2.5} style={{ marginRight: 6 }} /> Adaptive Learning Pathway</div>
                <div className="flow-legend">
                    {Object.entries(PHASE_CONFIG).map(([phase, cfg]) => (
                        <div key={phase} className="legend-item">
                            <span className="legend-dot" style={{ background: cfg.color }} />
                            {phase}
                        </div>
                    ))}
                </div>
            </div>

            <div className="flow-container">
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={NODE_TYPES}
                    fitView
                    fitViewOptions={{ padding: 0.25 }}
                    minZoom={0.4}
                    proOptions={{ hideAttribution: true }}
                >
                    <Background
                        color="rgba(255,255,255,0.04)"
                        gap={24}
                        variant={BackgroundVariant.Dots}
                    />
                    <Controls />
                    <MiniMap
                        nodeColor={(n) => {
                            const cfg = PHASE_CONFIG[n.data?.phase] || PHASE_CONFIG.Foundation;
                            return cfg.color;
                        }}
                        style={{ background: "rgba(15,17,32,0.9)" }}
                        maskColor="rgba(0,0,0,0.4)"
                    />
                </ReactFlow>
            </div>

            <div
                style={{
                    padding: "12px 24px",
                    borderTop: "1px solid var(--border)",
                    fontSize: 12,
                    color: "var(--text-muted)",
                }}
            >
                {rawNodes.length} modules · {rawEdges.length} prerequisite edges ·{" "}
                <span style={{ color: "var(--accent-blue)" }}>
                    Click any node to see reasoning trace
                </span>
            </div>
        </div>
    );
}

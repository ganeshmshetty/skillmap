import React, { useState, useRef, useEffect } from "react";
import { Terminal, ChevronDown, ChevronRight, Activity, FileText, Cpu, Link2, Target, Map, BookOpen, Loader2 } from "lucide-react";

const STAGE_COLORS = {
  extract: "var(--accent-blue)",
  skills: "var(--accent-purple)",
  anchor: "var(--on-surface)",
  gap: "var(--accent-coral)",
  pathway: "var(--accent-green)",
  catalog: "var(--phase-core)",
};

const STAGE_ICONS = {
  extract: <FileText size={16} strokeWidth={2.5} />,
  skills: <Cpu size={16} strokeWidth={2.5} />,
  anchor: <Link2 size={16} strokeWidth={2.5} />,
  gap: <Target size={16} strokeWidth={2.5} />,
  pathway: <Map size={16} strokeWidth={2.5} />,
  catalog: <BookOpen size={16} strokeWidth={2.5} />,
};

const METHOD_COLORS = {
  exact_title: { bg: "rgba(16, 185, 129, 0.15)", color: "#10b981" },
  alias: { bg: "rgba(59, 130, 246, 0.15)", color: "#3b82f6" },
  embedding: { bg: "rgba(168, 85, 247, 0.15)", color: "#a855f7" },
  substring: { bg: "rgba(245, 158, 11, 0.15)", color: "#f59e0b" },
  unmatch: { bg: "rgba(239, 68, 68, 0.15)", color: "#ef4444" },
  unmatched: { bg: "rgba(239, 68, 68, 0.15)", color: "#ef4444" },
};

export default function LiveFeed({ events }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  const groupedEvents = [];
  let currentAnchorGroup = null;

  events.forEach((ev) => {
    if (ev?.stage === "anchor") {
      // Group by both stage AND side to prevent mixed side groups if something skips
      const side = ev.data?.side || "unknown";
      if (!currentAnchorGroup || currentAnchorGroup.side !== side) {
        currentAnchorGroup = {
          id: `group-${ev.ts}-${Math.random()}`,
          type: "anchor_group",
          side: side,
          items: [],
        };
        groupedEvents.push(currentAnchorGroup);
      }
      currentAnchorGroup.items.push(ev);
    } else if (ev) {
      currentAnchorGroup = null;
      groupedEvents.push(ev);
    }
  });

  return (
    <div className="live-feed-card glass-card">
      <div className="live-feed-header">
        <Terminal size={16} strokeWidth={2.5} />
        <span>PIPELINE TRACE</span>
        <div className="live-feed-badge">
          <Activity size={12} className="pulse-icon" /> EXECUTION FEED
        </div>
      </div>
      <div className="live-feed-body" ref={containerRef}>
        {groupedEvents.map((item, i) => {
          const isLatest = i === groupedEvents.length - 1;
          if (item?.type === "anchor_group") {
            return <AnchorGroup key={item.id} group={item} isLatest={isLatest} />;
          }
          return <EventRow key={i} event={item} isLatest={isLatest} />;
        })}
        {events.length > 0 && (
          <div className="live-feed-pending slide-in">
            <Loader2 size={16} className="spin-icon" strokeWidth={2.5}/> 
            <span>Processing next sequence<span className="blinking-cursor">_</span></span>
          </div>
        )}
        {events.length === 0 && (
          <div className="live-feed-empty">Waiting for trace engine to connect...</div>
        )}
      </div>
    </div>
  );
}

function EventRow({ event, isLatest }) {
  if (!event) return null;
  return (
    <div className={`event-row slide-in ${isLatest ? 'latest-row' : ''}`}>
      <div className="event-icon" style={{ color: STAGE_COLORS[event.stage] || "var(--on-surface)" }}>
        {STAGE_ICONS[event.stage] || <Terminal size={14} strokeWidth={3} />}
      </div>
      <div className="event-detail">{event.detail}</div>
      <div className="event-ts">
        {event.ts ? new Date(event.ts).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second:'2-digit' }) : "--:--:--"}
      </div>
    </div>
  );
}

function AnchorGroup({ group, isLatest }) {
  const [expanded, setExpanded] = useState(false);

  if (!group?.items) return null;

  const exact = group.items.filter((i) => i.data?.method === "exact_title").length;
  const alias = group.items.filter((i) => i.data?.method === "alias").length;
  const embed = group.items.filter((i) => i.data?.method === "embedding").length;
  const unmatch = group.items.filter((i) => i.data?.method === "unmatched" || i.data?.method === "unmatch").length;

  return (
    <div className={`anchor-group slide-in ${isLatest ? 'latest-row' : ''}`}>
      <div 
        className="anchor-group-header" 
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown size={16} strokeWidth={3} /> : <ChevronRight size={16} strokeWidth={3} />}
        <span className="event-icon" style={{ color: STAGE_COLORS["anchor"] }}><Link2 size={16} strokeWidth={2.5}/></span>
        <span>O*NET Vector Anchoring ({(group.side || "unknown").toUpperCase()}) - {group.items.length} nodes</span>
        <div className="anchor-summary-badges">
          {exact > 0 && <span className="m-badge exact">{exact} EXACT</span>}
          {alias > 0 && <span className="m-badge alias">{alias} ALIAS</span>}
          {embed > 0 && <span className="m-badge embed">{embed} SEMANTIC</span>}
          {unmatch > 0 && <span className="m-badge unmatch">{unmatch} MISS</span>}
        </div>
      </div>
      
      {expanded && (
        <div className="anchor-group-items">
          {group.items.map((ev, i) => {
            const m = ev.data?.method || "unknown";
            const style = METHOD_COLORS[m] || { bg: "rgba(100,100,100,0.1)", color: "var(--outline)" };
            return (
              <div key={i} className="anchor-item">
                <div className="anchor-method" style={{ backgroundColor: style.bg, color: style.color }}>
                  {m.replace("_title", "")}
                </div>
                <div className="anchor-skill">{ev.data?.skill || "Unknown Skill"}</div>
                <div className="anchor-arrow">→</div>
                <div className="anchor-target">
                  {ev.data?.onet_id || "No equivalent taxonomy node"}
                </div>
                {ev.data?.score > 0 && m !== "unmatched" && (
                  <div className="anchor-score">{(ev.data.score * 100).toFixed(0)}%</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

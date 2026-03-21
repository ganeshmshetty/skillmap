import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, CheckCircle, PlayCircle, Clock } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function PathwayTracker() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/history/${id}`)
      .then((res) => res.json())
      .then((json) => {
        setData(json.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [id]);

  const updateStatus = async (moduleId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/pathway_modules/${moduleId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: newStatus })
      });
      
      if (res.ok) {
        // Optimistically update UI
        setData(prev => ({
          ...prev,
          modules: prev.modules.map(m => m.id === moduleId ? { ...m, status: newStatus } : m)
        }));
      }
    } catch (err) {
      console.error("Failed to update status", err);
    }
  };

  if (loading) return <div className="glass-card"><p>Loading pathway...</p></div>;
  if (!data) return <div className="glass-card"><p>Pathway not found.</p></div>;

  return (
    <div style={{ animation: "slideUp 0.4s ease" }}>
      <div className="results-header" style={{ marginBottom: '1.5rem' }}>
        <div>
          <Link to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary)', textDecoration: 'none', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
            <ArrowLeft size={16} /> Back to Dashboard
          </Link>
          <h1 className="section-title">{data.job_title} Curriculum</h1>
          <p className="section-subtitle">
            Match Score: {data.match_score}% • Generated: {new Date(data.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {data.modules?.map((mod, i) => (
          <div key={mod.id} style={{
            background: mod.status === 'Completed' ? 'rgba(0, 255, 0, 0.05)' : 'var(--surface-container)',
            border: `1px solid ${mod.status === 'Completed' ? 'var(--success, #4CAF50)' : 'var(--outline-variant)'}`,
            padding: '1rem 1.5rem',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', background: 'var(--surface-variant)', color: 'var(--on-surface-variant)', padding: '2px 6px', borderRadius: '4px' }}>
                  Phase {Math.floor(i / 3) + 1}
                </span>
                <h3 style={{ margin: 0, color: 'var(--on-surface)' }}>{mod.title}</h3>
              </div>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--on-surface-variant)', fontStyle: 'italic' }}>
                "{mod.justification}"
              </p>
            </div>
            
            <div style={{ display: 'flex', gap: '0.5rem', marginLeft: '1rem' }}>
              {mod.status === 'Pending' && (
                <button 
                  onClick={() => updateStatus(mod.id, 'In Progress')}
                  style={{ background: 'var(--primary-container)', color: 'var(--on-primary-container)', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                >
                  <PlayCircle size={14} /> Start
                </button>
              )}
              {mod.status === 'In Progress' && (
                <button 
                  onClick={() => updateStatus(mod.id, 'Completed')}
                  style={{ background: 'var(--success, #4CAF50)', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                >
                  <CheckCircle size={14} /> Mark Done
                </button>
              )}
              {mod.status === 'Completed' && (
                <span style={{ color: 'var(--success, #4CAF50)', display: 'flex', alignItems: 'center', gap: '0.25rem', fontWeight: 'bold' }}>
                  <CheckCircle size={18} /> Completed
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
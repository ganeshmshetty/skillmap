import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, CheckCircle } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function Dashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/history`)
      .then((res) => res.json())
      .then((data) => {
        setHistory(data.data || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="glass-card" style={{ animation: "slideUp 0.4s ease" }}>
      <div className="results-header">
        <div>
          <h1 className="section-title">Saved Learning Pathways</h1>
          <p className="section-subtitle">Track your progress across multiple analyses</p>
        </div>
        <Link to="/" className="btn-reset" style={{ textDecoration: 'none' }}>
          New Analysis
        </Link>
      </div>

      {loading ? (
        <p>Loading history...</p>
      ) : history.length === 0 ? (
        <p>No pathways generated yet. Run an analysis first!</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {history.map((run) => (
            <div key={run.id} style={{ 
              background: 'var(--surface-container)', 
              padding: '1rem 1.5rem', 
              borderRadius: '8px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              border: '1px solid var(--outline-variant)'
            }}>
              <div>
                <h3 style={{ margin: '0 0 0.5rem', color: 'var(--on-surface)' }}>{run.job_title}</h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--on-surface-variant)' }}>
                  Match Score: {run.match_score}% • Date: {new Date(run.created_at).toLocaleDateString()}
                </p>
              </div>
              <Link 
                to={`/pathway/${run.id}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 1rem',
                  background: 'var(--primary)',
                  color: 'var(--on-primary)',
                  textDecoration: 'none',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  fontWeight: '600'
                }}
              >
                Track Pathway <ExternalLink size={16} />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
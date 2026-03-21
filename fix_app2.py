import re

with open('temp.txt', 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(
    r'(?s)<header className="header">.*?</main>',
    '''<header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="header-logo"><BrainCircuit size={20} strokeWidth={2.5} color="var(--on-surface)" /></div>
            <div className="header-title">AI-Adaptive Onboarding Engine</div>
            <div className="header-badge">Hackathon 2026</div>
          </div>
          <nav>
            <Link to="/dashboard" style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '0.5rem', 
              color: 'var(--on-surface)',
              textDecoration: 'none',
              background: 'var(--surface-container)',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              fontWeight: '600'
            }}>
              <LibraryBig size={16} /> Pathway Library
            </Link>
          </nav>
        </header>

        {/* ---- Main Routing ---- */}
        <main className="main-content">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/pathway/:id" element={<PathwayTracker />} />
            <Route path="/" element={
              <>
                <StepIndicator current={step} />

                {/* UPLOAD */}
                {step === STEPS.UPLOAD && (
                  <div className="glass-card" style={{ animation: 'slideUp 0.4s ease' }}>
                    <UploadPanel onSubmit={handleSubmit} error={error} />
                  </div>
                )}

                {/* PROCESSING */}
                {step === STEPS.PROCESSING && (
                  <ProgressBar
                    jobId={jobId}
                    apiBase={API_BASE_URL}
                    onComplete={handleComplete}
                    onError={handlePollError}
                  />
                )}

                {/* RESULTS */}
                {step === STEPS.RESULTS && result && (
                  <div style={{ animation: 'slideUp 0.4s ease' }}>
                    <div className="results-header">
                      <div>
                        <h1 className="section-title">Your Learning Pathway</h1>
                        <p className="section-subtitle">
                          {result.pathway?.nodes?.length || 0} personalized modules · grounded, hallucination-free recommendations
                        </p>
                      </div>
                      <button
                        id="reset-btn"
                        className="btn-reset"
                        onClick={handleReset}
                      >
                        New Analysis
                      </button>
                    </div>

                    {/* Metric Cards */}
                    <SummaryCards result={result} />

                    {/* Skill Gap Chart */}
                    <SkillGapHeatmap gapVector={result.gap_vector || buildGapFromPathway(result)} />

                    {/* React Flow DAG */}
                    <PathwayFlowGraph
                        pathway={result.pathway}
                        onSelectModule={handleSelectModule}
                    />
                  </div>
                )}
              </>
            } />
          </Routes>
        </main>''',
    content
)

new_content = new_content.replace("import { useState } from 'react';", "import { useState } from 'react';\\nimport { Routes, Route, Link } from 'react-router-dom';\\nimport Dashboard from './Dashboard';\\nimport PathwayTracker from './PathwayTracker';\\nimport { LibraryBig, BrainCircuit } from 'lucide-react';")
new_content = new_content.replace("import { BrainCircuit } from 'lucide-react';\\n", "")

with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(new_content)

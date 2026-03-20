import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [resume, setResume] = useState(null);
  const [jd, setJd] = useState(null);
  const [status, setStatus] = useState("Idle");
  const [result, setResult] = useState(null);

  async function handleAnalyze(event) {
    event.preventDefault();

    if (!resume || !jd) {
      setStatus("Select both a resume and a job description file.");
      return;
    }

    setStatus("Uploading files...");

    const formData = new FormData();
    formData.append("resume", resume);
    formData.append("jd", jd);

    const analyzeResp = await fetch(`${API_BASE_URL}/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!analyzeResp.ok) {
      setStatus("Analyze request failed.");
      return;
    }

    const analyzeData = await analyzeResp.json();
    setStatus(`Job queued: ${analyzeData.job_id}`);

    const resultResp = await fetch(`${API_BASE_URL}/result/${analyzeData.job_id}`);
    if (!resultResp.ok) {
      setStatus("Could not fetch result.");
      return;
    }

    const resultData = await resultResp.json();
    setResult(resultData);
    setStatus("Ready");
  }

  return (
    <main className="page">
      <section className="panel">
        <h1>AI-Adaptive Onboarding Engine</h1>
        <p className="subtitle">Initial bootstrap UI for upload and API connectivity checks.</p>

        <form onSubmit={handleAnalyze} className="form">
          <label>
            Resume File
            <input type="file" onChange={(e) => setResume(e.target.files?.[0] || null)} />
          </label>

          <label>
            Job Description File
            <input type="file" onChange={(e) => setJd(e.target.files?.[0] || null)} />
          </label>

          <button type="submit">Analyze</button>
        </form>

        <p className="status">Status: {status}</p>

        {result ? <pre>{JSON.stringify(result, null, 2)}</pre> : null}
      </section>
    </main>
  );
}

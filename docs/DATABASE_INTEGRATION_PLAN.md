# Database Integration Plan: Historic Analysis & Learning Pathways Dashboard

This document outlines the detailed steps to integrate a cloud database into the current architecture to store previous resume analyses, skill gaps, and recommended learning pathways, and how to build a frontend dashboard to review and update them.

## Recommended Free Cloud Databases

For a free, cloud-hosted database that integrates perfectly with a Python/FastAPI backend, here are the top choices:

1. **Supabase (PostgreSQL) - Highly Recommended**
   * **Why it's great:** Excellent free tier (500MB DB size, unlimited API requests). It gives you a full PostgreSQL database. Since your data is highly relational (Analyses -> Gaps -> Pathways), a relational DB is perfect. You can use standard SQLAlchemy with `psycopg2` to connect to it.
2. **MongoDB Atlas (NoSQL)**
   * **Why it's great:** Extremely generous free tier (512MB storage). Since AI outputs are often JSON, storing the entire nested document (Analysis + Gaps + Pathways) in a single MongoDB collection can be very seamless. You would use `motor` or `pymongo` in FastAPI.
3. **Neon (Serverless PostgreSQL)**
   * **Why it's great:** Gives you a generous free Postgres DB with branching features. 

*For the scope of this plan, we will assume a **PostgreSQL** cloud database (like Supabase or Neon) using SQLAlchemy, as it provides strict schema structures for the AI outputs.*

---

## 1. Database Schema Design

If you want to **strictly store the generated pathway** (without tracking every individual skill gap in the database), the schema becomes much simpler.

### Proposed Tables

**`analyses` table** (The core record of a run)
*   `id` (Primary Key, Integer or UUID)
*   `created_at` (Timestamp)
*   `job_title` (String) - To help the user identify which job this was for.
*   `match_score` (Float/Integer) - Overall match score.

**`pathway_modules` table** (The actual generated curriculum for that analysis)
*   `id` (Primary Key, Integer)
*   `analysis_id` (Foreign Key -> `analyses.id`)
*   `module_id` (String) - Maps to your `modules.json` or generated module IDs.
*   `title` (String) - E.g., "Advanced React Hooks"
*   `status` (String) - Default: `Pending`. Can be updated to `In Progress` or `Completed`.
*   `order_index` (Integer) - To preserve the Topological Sort order.
*   `justification` (Text) - The AI reasoning for why this module is needed.

---

## 2. Backend Integration (FastAPI / Python)

### Step 2.1: Setup SQLAlchemy
Create a new file `api/app/database.py` to handle the SQLite connection.

```python
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./dashboard_history.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AnalysisResult(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    job_title = Column(String, index=True)
    match_score = Column(Float)
    
    # Relationships
    modules = relationship("PathwayModule", back_populates="analysis", cascade="all, delete-orphan", order_by="PathwayModule.order_index")

class PathwayModule(Base):
    __tablename__ = "pathway_modules"
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    module_id = Column(String)
    title = Column(String)
    status = Column(String, default="Pending") # Pending, In Progress, Completed
    order_index = Column(Integer)
    justification = Column(String)

    analysis = relationship("AnalysisResult", back_populates="modules")

Base.metadata.create_all(bind=engine)
```

### Step 2.2: Update the Parsing Endpoint
In `api/app/main.py`, modify the main POST endpoint (e.g., `/analyze`) to save the AI output to the database before returning the JSON response to the user.

```python
from app.database import SessionLocal, AnalysisResult
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/analyze")
async def analyze_resume(request: Request, db: Session = Depends(get_db)):
    # ... run your AI extraction and pathway generation logic ...
    
    # 1. Save Header (Analysis)
    new_analysis = AnalysisResult(
        job_title=extracted_job_title,
        match_score=calculated_score
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)
    
    # 2. Iterate through `pathway.nodes` (the topologically sorted list)
    for index, node in enumerate(pathway.nodes):
        pm = PathwayModule(
            analysis_id=new_analysis.id,
            module_id=node.module_id,
            title=node.title,
            status="Pending",
            order_index=index,
            justification=node.justification
        )
        db.add(pm)
    
    db.commit()
    
    return ai_results

### Step 2.3: Create Dashboard & Update Endpoints
Add new GET/PUT endpoints in `api/app/main.py` so the frontend can read the pathways and the user can update statuses.

```python
@app.get("/history")
async def get_history(limit: int = 10, db: Session = Depends(get_db)):
    # Fetch recent analyses (just the headers)
    analyses = db.query(AnalysisResult).order_by(AnalysisResult.created_at.desc()).limit(limit).all()
    return analyses

@app.get("/history/{analysis_id}")
async def get_history_detail(analysis_id: int, db: Session = Depends(get_db)):
    # Fetch specific analysis with its entire pathway mapping
    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == analysis_id).first()
    return analysis # The ORM will automatically embed `analysis.modules`

@app.put("/pathway_modules/{pm_id}")
async def update_pathway_module(pm_id: int, status: str, db: Session = Depends(get_db)):
    # Allow users to mark a specific module as 'In Progress' or 'Completed'
    pm = db.query(PathwayModule).filter(PathwayModule.id == pm_id).first()
    if not pm:
        raise HTTPException(status_code=404, detail="Module not found")
    
    pm.status = status
    db.commit()
    return {"message": "Status updated", "final_status": pm.status}
```

---

## 3. Frontend Integration (React / Vite)

### Step 3.1: Create a Dashboard Component
Create `frontend/src/Dashboard.jsx` to list previous runs. Connect it to the backend `/history` endpoint.

```jsx
import React, { useEffect, useState } from 'react';

export default function Dashboard() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetch('/api/history') // adjust URL based on your proxy setup
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="dashboard-container">
      <h2>Previous Analyses</h2>
      <div className="history-grid">
        {history.map(item => (
          <div key={item.id} className="history-card">
            <h3>{item.job_title}</h3>
            <p>Match: {item.match_score}%</p>
            <p>Date: {new Date(item.created_at).toLocaleDateString()}</p>
            <button onClick={() => viewPathway(item.id)}>Review Pathway</button>
          </div>
        ))}
      </div>
      
      {/* 
        Inside the review view (not fully coded here):
        1. Call GET `/history/{id}` to fetch all the modules in their preserved order.
        2. Render them in a list or UI pipeline.
        3. For each module, have buttons for 'Start Course' (which triggers PUT `status`='In Progress')
           and 'Mark Done' (which triggers PUT `status`='Completed').
      */}
    </div>
  );
}
```

### Step 3.2: Update the Main App View
Modify `frontend/src/App.jsx` to include navigation state to toggle between the main "Analysis" view (UploadPanel/LiveFeed) and the new "Dashboard" view.

```jsx
import { useState } from 'react';
import UploadPanel from './UploadPanel';
import Dashboard from './Dashboard';

function App() {
  const [currentView, setCurrentView] = useState('upload'); // 'upload' | 'dashboard'

  return (
    <div>
      <nav>
        <button onClick={() => setCurrentView('upload')}>New Analysis</button>
        <button onClick={() => setCurrentView('dashboard')}>Dashboard</button>
      </nav>
      
      {currentView === 'upload' ? (
        <UploadPanel />
        /* Include other existing components */
      ) : (
        <Dashboard />
      )}
    </div>
  );
}
export default App;
```

---

## Next Steps to Implement
1. **Install Dependencies Setup:** Run `pip install sqlalchemy` in your Python environment if it's not already installed.
2. **Implement `database.py`:** Create the schema in the `api/app/` folder.
3. **Wire up Backend:** Start persisting the results synchronously inside your FastAPI endpoints.
4. **Wire up Frontend:** Build the dashboard UI to consume the `/history` APIs.

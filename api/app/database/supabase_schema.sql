-- Copy and paste this into the Supabase SQL Editor

-- 1. Create Analyses table
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    job_title TEXT NOT NULL,
    match_score REAL NOT NULL
);

-- 2. Create Pathway Modules table
CREATE TABLE pathway_modules (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    module_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'Pending' NOT NULL,
    order_index INTEGER NOT NULL,
    justification TEXT
);

-- Optional: Add Row Level Security (RLS) policies if you require users to log in later
-- For now, allowing all access for anon keys
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE pathway_modules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to analyses" ON analyses FOR ALL USING (true);
CREATE POLICY "Allow all access to modules" ON pathway_modules FOR ALL USING (true);

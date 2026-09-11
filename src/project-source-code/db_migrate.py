from sqlalchemy import text
from db.database import engine

if engine:
    with engine.connect() as conn:
        print("Checking/updating database schema...")
        conn.execute(text("ALTER TABLE dataset_runs ADD COLUMN IF NOT EXISTS run_code VARCHAR(50);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_dataset_runs_run_code ON dataset_runs (run_code);"))
        # Update any null run_codes with generated ones
        conn.execute(text("UPDATE dataset_runs SET run_code = 'DC4X-' || SUBSTRING(id, 1, 6) WHERE run_code IS NULL;"))
        conn.commit()
        print("Schema updated successfully.")

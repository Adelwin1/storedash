# StoreDash Backend

FastAPI + SQLAlchemy MVP backend.

Run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The default development database is SQLite (`storedash.db`) and is created automatically on first startup.

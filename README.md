# deed-admin

## How to Run

1. Activate virtualenv:
& "E:/Data Science/Agentic AI/env/Scripts/Activate.ps1"

2. Run FastAPI backend:

uvicorn src.backend.app:app --reload

or

uvicorn src.backend.app:app --reload --host 127.0.0.1 --port 8000

3. Run Panel dashboards:

panel serve frontend/admin_dashboard.py --port 5006
panel serve frontend/dashboard_user.py --port 5007

4. Access Landing Page:

http://127.0.0.1:8000/
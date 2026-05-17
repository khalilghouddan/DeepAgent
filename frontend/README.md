# Frontend (React + Vite)

This folder contains a separate React frontend scaffold for the Deep Agent project.

## Run

Start backend API (from project root):

```bash
pip install -r requirements.txt
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

Then run frontend:

```bash
cd frontend
npm install
npm run dev
```

By default, Vite runs at `http://localhost:5173`.

## Notes

- The `Submit` button calls `POST /api/research` and displays the returned result.
- The query, language, and log level are sent to the backend API.

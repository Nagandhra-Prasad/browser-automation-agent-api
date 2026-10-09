# Browser Automation Agent API

FastAPI backend for natural-language browser automation: **JWT auth**, **MongoDB**, **OpenAI task planning**, and **Playwright** execution. Matches the architecture in your project diagrams (User → API → AI planning → Playwright → Results → Reports).

## Stack

| Layer | Technology |
|--------|------------|
| API | FastAPI + Uvicorn |
| Database | MongoDB (`motor`) |
| Auth | JWT (Bearer) |
| AI planning / summary | **Ollama** (default, free/local) or Groq / Gemini / OpenAI |
| Browser automation | Playwright (Chromium) |
| Frontend (your Angular app) | HTTP JSON + `Authorization: Bearer <token>` |

## Quick start

### 1. Prerequisites

- Python 3.11+
- MongoDB running locally (`mongodb://localhost:27017`) or [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) URI
- [Ollama](https://ollama.com) for free local AI (recommended), **or** a free Groq/Gemini key (see `.env.example`)

### 2. Setup

```bash
cd browser-automation-agent-api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Edit .env: MONGODB_URL, JWT_SECRET
# Free AI (recommended):
ollama pull llama3.2
```

### 3. Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: http://localhost:8000/docs  
- ReDoc: http://localhost:8000/redoc  
- Health: http://localhost:8000/api/v1/health  

## Environment variables (`.env`)

See `.env.example`. Required for production:

- `MONGODB_URL` – MongoDB connection string  
- `JWT_SECRET` – long random string (min 32 characters)  
- `AI_PROVIDER=ollama` – default; run Ollama locally (`ollama pull llama3.2`)  
- Or `AI_PROVIDER=groq` + `GROQ_API_KEY` from [Groq console](https://console.groq.com/keys) (free)  
- Or `AI_PROVIDER=gemini` + `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) (free tier)  
- `CORS_ORIGINS` – Angular dev URL(s), default `http://localhost:4200`

## MongoDB collections (ER model)

| Collection | Purpose |
|------------|---------|
| `users` | `name`, `email`, `password_hash` |
| `tasks` | `task_name`, `command`, `website`, `status`, `plan` |
| `sessions` | `task_id`, `start_time`, `end_time`, `status` |
| `results` | `session_id`, `task_id`, `data`, `summary`, `timestamp` |

## API reference (Postman / Angular)

Base URL: **`http://localhost:8000/api/v1`**

All protected routes need header:

```http
Authorization: Bearer <access_token>
```

### Auth

| Method | Path | Body | Notes |
|--------|------|------|--------|
| POST | `/auth/register` | `{ "name", "email", "password" }` | Returns `access_token` + `user` |
| POST | `/auth/login` | `{ "email", "password" }` | Returns `access_token` |
| GET | `/auth/me` | — | Current user profile |

### Tasks

| Method | Path | Body |
|--------|------|------|
| POST | `/tasks` | `{ "task_name", "command", "website" }` — `website` must be a full URL |
| GET | `/tasks` | List history for logged-in user |
| GET | `/tasks/{task_id}` | Single task |
| GET | `/tasks/{task_id}/sessions` | Browser sessions for task |

### Automation

| Method | Path | Body |
|--------|------|------|
| POST | `/automation/tasks/{task_id}/start` | Optional `{ "headless": true }` |

Flow: **plan (AI)** → **run Playwright steps** → **clean data** → **save result** → task `status: completed`.

### Results & reports

| Method | Path |
|--------|------|
| GET | `/results/history` |
| GET | `/results/task/{task_id}` |
| GET | `/results/session/{session_id}` |
| GET | `/reports/task/{task_id}/download` | JSON file download |

### Health

| Method | Path |
|--------|------|
| GET | `/health` | MongoDB + OpenAI config status |

## Postman

1. Import: `postman/Browser-Automation-Agent-API.postman_collection.json`
2. Collection variable `baseUrl` = `http://localhost:8000/api/v1`
3. Run **Auth - Register** or **Auth - Login** (saves `accessToken` automatically)
4. Run **Tasks - Create** (saves `taskId`)
5. Run **Automation - Start** (may take 30–60s)
6. Run **Results - By Task** or **Reports - Download JSON**

## Angular frontend integration

1. **Base API URL** in Angular `environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1',
};
```

2. **HTTP interceptor** – attach JWT:

```typescript
req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
```

3. **Suggested screens → endpoints**

| UI module (diagram) | API calls |
|---------------------|-----------|
| Login | `POST /auth/login` — store `access_token` |
| Register | `POST /auth/register` |
| Task input | `POST /tasks` with natural language `command` + `website` |
| Start automation | `POST /automation/tasks/{id}/start` |
| Dashboard / history | `GET /tasks`, `GET /results/history` |
| View result | `GET /results/task/{task_id}` or `/results/session/{session_id}` |
| Report download | `GET /reports/task/{task_id}/download` (save blob as JSON) |
| User profile | `GET /auth/me` |

4. **CORS** – ensure `CORS_ORIGINS` in `.env` includes your Angular origin (`http://localhost:4200`).

5. **Example create task (HttpClient)**

```typescript
this.http.post(`${environment.apiUrl}/tasks`, {
  task_name: 'Java jobs Chennai',
  command: 'Find Java developer jobs in Chennai',
  website: 'https://www.google.com',
}, { headers: this.authHeaders });
```

## Project layout

```
app/
  api/v1/          # REST routes
  core/            # JWT, dependencies
  repositories/    # MongoDB access
  schemas/         # Pydantic models
  services/        # AI, Playwright, orchestration
  config.py
  database.py
  main.py
postman/           # Postman collection
```

## Notes

- First automation run downloads Chromium via Playwright if not installed.
- Screenshots (when planned) are stored under `screenshots/`.
- With `AI_PROVIDER=none` or if Ollama is not running, planning uses a minimal navigate + extract fallback; automation still runs.

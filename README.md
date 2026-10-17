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
python -m playwright install chromium   # or: auto-downloads to `.pw-browsers/` on API startup (dev)
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
- Root `http://localhost:8000/` returns 404 — use `/docs` or `/api/v1/health` instead.

## MongoDB (local Mac via Homebrew)

**One-time install** (you do not repeat these every day):

```bash
brew tap mongodb/brew
brew trust mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Start** MongoDB (after install, or if you stopped it):

```bash
brew services start mongodb-community@7.0
```

**Stop** MongoDB:

```bash
brew services stop mongodb-community@7.0
```

**Restart** MongoDB:

```bash
brew services restart mongodb-community@7.0
```

**Check status:**

```bash
brew services list | grep mongo
```

**MongoDB Compass** connection string (matches `.env`):

```text
mongodb://localhost:27017
```

Database name: **`browser_automation`** (`MONGODB_DB_NAME` in `.env`).

**Docker alternative** (if you use Docker Desktop): `docker compose up -d` in this repo — stop with `docker compose down`.

**Atlas alternative:** set `MONGODB_URL` to your `mongodb+srv://...` string; no local `brew services` needed.

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

### Chat (for Angular UI)

| Method | Path | Body |
|--------|------|------|
| GET | `/chat/conversations` | List user conversations |
| POST | `/chat/conversations` | `{ "title" }` — start new thread |
| GET | `/chat/conversations/{id}` | Conversation + all **messages** |
| POST | `/chat` | `{ "message", "conversation_id"?, "website"?, "headless"? }` |

MongoDB collections: **`conversations`**, **`messages`** (user + agent text; agent row stores full AI metadata: jobs, status, plan, etc.).

- **"hi" / greetings** → instant reply, no browser (`status: conversation`).
- **Job questions** → agent opens **Google Jobs** automatically (no URL from user) → returns `jobs[]` table fields.
- Job runs: create task → automation → `reply`, `summary`, `data`, `jobs`.
- Every send persists **user message** and **agent reply** for UI refresh/history.

### Users (management)

| Method | Path |
|--------|------|
| GET | `/users` | List all users — **admin JWT only** |

### Dashboard

| Method | Path |
|--------|------|
| GET | `/dashboard/summary` | Stats for user or admin |

### Auth roles

| Method | Path | Notes |
|--------|------|--------|
| POST | `/auth/register` | `{ name, email, password, role: "user"\|"admin", admin_code? }` |
| POST | `/auth/onboarding-complete` | Mark guided tour finished |

Admin registration requires `admin_code` matching `ADMIN_REGISTRATION_CODE` in `.env` (default `admin123` for dev).

### Results & reports

| Method | Path |
|--------|------|
| GET | `/results/table` | Job results table (own rows; **admin** sees all users) |
| GET | `/results/history` |
| GET | `/results/task/{task_id}` |
| GET | `/results/session/{session_id}` |
| GET | `/reports/task/{task_id}/download` | JSON file download |

### Health

| Method | Path |
|--------|------|
| GET | `/health` | MongoDB + AI provider status |

## Postman

1. Import: `postman/Browser-Automation-Agent-API.postman_collection.json`
2. Collection variable `baseUrl` = `http://localhost:8000/api/v1`
3. Run **Auth - Register** or **Auth - Login** (saves `accessToken` automatically)
4. Run **Tasks - Create** (saves `taskId`)
5. Run **Automation - Start** (may take 30–60s)
6. Run **Results - By Task** or **Reports - Download JSON**

## Frontend repo (`browser-automation-agent-web`)

A separate Angular app is wired to this API:

- Set `apiUrl: 'http://localhost:8000/api/v1'` in `browser-automation-web/src/environments/environment.ts`
- Run API on port **8000**, frontend with `ng serve` on **4200**
- Chat UI uses **`POST /api/v1/chat`** (creates task + runs automation + returns agent reply)

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

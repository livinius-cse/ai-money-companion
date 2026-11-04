# AI Money Companion (KDP OS)

> Web-based AI-assisted Amazon KDP Publishing Operating System designed to manage an author's publishing portfolio with strict compliance, local-first zero-cost development, and mandatory human-in-the-loop approvals.

---

## 🏛 System Architecture Overview

```
ai-money-companion/
├── apps/
│   ├── api/                   # Python FastAPI service
│   │   ├── app/
│   │   │   ├── api/v1/        # Auth, Books, Studio, Preflight, Exports
│   │   │   ├── core/          # Argon2id, JWT, Signed CSRF, Rate Limiter
│   │   │   ├── db/            # SQLite WAL mode & Alembic migrations
│   │   │   ├── models/        # SQLAlchemy 2.0 ORM models
│   │   │   ├── schemas/       # Pydantic validation schemas
│   │   │   └── services/      # Publishing domain logic
│   │   └── tests/             # Pytest unit & integration suite
│   └── web/                   # Next.js App Router (TypeScript, Tailwind)
│       └── src/
│           ├── app/           # App Router pages (login, dashboard, studio)
│           ├── hooks/         # React Auth & state hooks
│           ├── lib/           # Authenticated API client (CSRF & Cookies)
│           └── types/         # Auto-generated OpenAPI typings
├── storage/                   # Local file storage (Git-ignored)
└── scripts/                   # Development, testing, and sync automation
```

---

## 🔒 Security Architecture (Milestone 1)

1. **Authentication:**
   - Password hashing with **Argon2id** (`argon2-cffi`).
   - Sessions issued via **`HttpOnly`**, **`SameSite=Strict`** cookies (inaccessible to JavaScript).
   - Rate limiting on `/api/v1/auth/login` to prevent brute-force attacks (max 5 attempts/minute per IP).
2. **CSRF & Origin Protection:**
   - Double-submit signed CSRF token using HMAC-SHA256 (`csrf_token`).
   - Session/User identity binding: CSRF tokens are bound to the authenticated user ID.
   - Origin / Referer validation against `ALLOWED_ORIGINS` for all state-changing requests.
3. **Secret Isolation:**
   - API keys and database connection secrets remain strictly on the backend.
   - Frontend accesses backend endpoints via type-safe API client forwarding credentials.

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **pnpm** (or npm)

### 2. Backend Setup (`apps/api`)
```powershell
# Navigate to API directory
cd apps/api

# Create & activate virtual environment
py -3 -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations & start FastAPI
python -m uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/api/docs`
- Health Probe: `http://localhost:8000/api/v1/health`

### 3. Frontend Setup (`apps/web`)
```powershell
# Navigate to web directory
cd apps/web

# Install packages
pnpm install

# Start Next.js development server
pnpm run dev
```
- Web Application: `http://localhost:3000`

### 4. Running Backend Tests
```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest tests -v
```

### 5. Synchronizing OpenAPI Types
```powershell
.\scripts\generate-types.ps1
```

---

## 📅 Roadmap & Milestones

- [x] **Milestone 1: Monorepo Foundations, Security & Auth** (Completed)
- [ ] **Milestone 2: Mock AI Engine & Initial Services (Planning & Metadata)**
- [ ] **Milestone 3: Product Studio — Concept, Content & Illustrations**
- [ ] **Milestone 4: WeasyPrint Interior Layout, Cover Math & Quality Checks**
- [ ] **Milestone 5: Pre-Flight QA & 5-Way Cryptographic Approval Gate**
- [ ] **Milestone 6: KDP Package Exporter & Sales Ingestion**

# SecureEntry Lens

Security Verification & Incident Intelligence. This security-first, human-reviewed workflow combines deterministic checks against synthetic credentials with public context and an evidence-linked Access Integrity Case Card.

## Current status

MVP scaffold on branch feat/secureentry-lens-p0: synthetic access checks, TinyFish Search → Fetch integration, Case Card composition, React dashboard, and initial tests. P1 vision is explicitly unavailable rather than simulated. The code has not yet been executed in a local checkout.

## Safety and scope

- Use synthetic references only: SYN-1042, SYN-1043, SYN-1044.
- Demo only, not production access control or life-safety certification.
- No face recognition, persistent identity tracking, person-level risk scoring, or automated enforcement.
- Public notices are context only; they do not implicate a person or change a credential decision.
- No match, stale context, missing inputs, and provider errors are never an all-clear.
- TinyFish page content is untrusted. Keep the API key on the backend.

## Architecture

- Frontend: React + TypeScript + Vite
- API: Python + FastAPI + Pydantic
- Access rules: deterministic Python rules with synthetic in-memory fixtures
- External context: TinyFish Search API followed by TinyFish Fetch API
- Persistence: none in P0
- P1 vision: deferred; endpoint explicitly reports unavailable

## Prerequisites

Python 3.11+ (plan targets Python 3.12), Node.js 20+, npm, and a TinyFish API key for live Search → Fetch. Credential checks and Case Card composition can be tested without a key.

## Backend setup

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment on macOS/Linux:
```bash
source .venv/bin/activate
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the environment Python directly without changing execution policy:
```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Install dependencies and create local configuration:
```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Add your own TINYFISH_API_KEY to backend/.env. Do not commit it. The app reads environment variables; it does not automatically load .env files. Export them before starting the API.

macOS/Linux:
```bash
set -a
source .env
set +a
uvicorn app.main:app --reload
```

Windows PowerShell:
```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') {
    [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
  }
}
python -m uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  
Health check: http://127.0.0.1:8000/api/health

## Frontend setup

In a second terminal from the repository root:
```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally http://localhost:5173. Set VITE_API_BASE_URL only if the API is not at http://localhost:8000.

## Tests

From the repository root:
```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands are defined by repository files; tests/builds have not yet been executed in a local checkout during this remote repository change. Treat the implementation as unverified until commands are run and results recorded.

## API routes

- GET /api/health
- POST /api/credential/check
- POST /api/context/search-fetch
- POST /api/cases/compose
- POST /api/vision/observe — explicitly unavailable in P0

Authoritative schemas, enum values, nullability rules, examples, and acceptance criteria are in docs/contracts.md.

## Example credential check

```bash
curl -X POST http://127.0.0.1:8000/api/credential/check \
  -H 'Content-Type: application/json' \
  -d '{"credential_ref":"SYN-1042","zone":"LAB-A","checked_at":"2026-10-20T09:00:00Z"}'
```

## Next steps

1. Run backend tests and frontend typecheck/build; fix failures before demoing.
2. Configure TinyFish and verify live Search → Fetch with a real public source, including no-match/stale/provider-error paths.
3. Add integration tests and UI failure-state tests.
4. Keep P1 vision and review/audit persistence deferred until P0 is verified.

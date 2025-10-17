---
title: LLM Code Deployment API
emoji: 👀
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

## LLM Code Deployment API

A minimal FastAPI service that accepts a JSON POST to build and deploy a small web app using an LLM, pushes to GitHub, enables Pages, and notifies an evaluation endpoint.

### API
- POST `/api-endpoint`
  - Body fields: `email`, `secret`, `task`, `round`, `nonce`, `brief`, `checks`, `evaluation_url`, `attachments`
  - Verifies `secret` against `secret_key` environment variable.
  - Responds immediately with `{ "message": "Accepted" }` and processes in background.

### Environment variables
- `secret_key`: Shared secret for request verification.
- `ai_token`: Token for the LLM provider.
- `base_url`: Base URL for the LLM provider (if required).
- `github_token`: GitHub personal access token with `repo` scope.
- `github_username`: Your GitHub username.

### Local run
```bash
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker build -t llm-deploy-api .
docker run -p 8000:8000 ^
  -e secret_key=your-secret ^
  -e ai_token=sk-... ^
  -e base_url=https://api.example.com ^
  -e github_token=ghp_... ^
  -e github_username=your-user ^
  llm-deploy-api
```

### Example request
```bash
curl http://localhost:8000/api-endpoint \
  -H "Content-Type: application/json" \
  -d @request.json
```

### Notes
- Minimal edits were made to fix typos and make the endpoint work.
- Background processing sends results to `evaluation_url` with retry backoff.

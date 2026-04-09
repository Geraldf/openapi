# Docker DB API

Auto-generated REST API for a PostgreSQL database, built with FastAPI. Exposes all tables as paginated JSON endpoints with API key authentication and a RapiDoc UI.

## Features

- Auto-discovers all tables in the `public` schema
- Paginated row listing with `limit` / `offset`
- Single-row lookup by `id`
- API key authentication via `X-API-Key` header
- RapiDoc UI at `/docs`

## Requirements

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv)

## Setup

```bash
# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
API_KEY=your-secret-key
```

## Running

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## API Endpoints

All endpoints require the `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | List all tables and endpoint URLs |
| `GET` | `/tables` | All tables with column definitions |
| `GET` | `/tables/{table}` | Paginated rows (`?limit=100&offset=0`) |
| `GET` | `/tables/{table}/columns` | Column schema for a table |
| `GET` | `/tables/{table}/{id}` | Single row by `id` |

**Example:**

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/tables/users
```

## Docker

### Build and run locally

```bash
docker build -t docker-db-api .

docker run -d \
  -p 7000:7000 \
  --env-file .env \
  docker-db-api
```

### GitHub Container Registry

Images are automatically built and pushed to `ghcr.io` on every push to `main`:

```bash
docker pull ghcr.io/geraldf/openapi:latest

docker run -d \
  -p 7000:7000 \
  --env-file .env \
  ghcr.io/geraldf/openapi:latest
```

## CI/CD

GitHub Actions workflow (`.github/workflows/docker.yml`):

- **Pull requests** → builds the image (no push)
- **Push to `main`** → builds and pushes to `ghcr.io` with tags `latest`, `main`, and `sha-<commit>`

No secrets configuration needed — uses the automatic `GITHUB_TOKEN`.

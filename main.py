import os
from contextlib import asynccontextmanager
from typing import Any


import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key")


def require_api_key(key: str = Security(api_key_header)):
    if not API_KEY:
        raise RuntimeError("API_KEY is not set. Check your .env file.")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def get_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        return [row[0] for row in cur.fetchall()]


def get_columns(conn, table: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [
            {
                "name": row[0],
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
            }
            for row in cur.fetchall()
        ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Check your .env file.")
    try:
        conn = get_conn()
        conn.close()
    except Exception as e:
        raise RuntimeError(f"Cannot connect to database: {e}") from e
    yield


app = FastAPI(
    title="Docker DB API",
    description="Auto-generated REST API for the dbframe PostgreSQL database.",
    version="1.0.1",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


@app.get("/docs", include_in_schema=False)
async def rapidoc():
    return HTMLResponse("""
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Docker DB API</title>
    <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
  </head>
  <body>
    <rapi-doc
      spec-url="/openapi.json"
      theme="dark"
      bg-color="#1a1a2e"
      primary-color="#6c63ff"
      nav-bg-color="#16213e"
      nav-text-color="#e0e0e0"
      nav-hover-bg-color="#0f3460"
      nav-hover-text-color="#ffffff"
      text-color="#e0e0e0"
      header-color="#1a1a2e"
      render-style="read"
      layout="row"
      show-header="true"
      allow-search="true"
      allow-try="true"
      font-size="large"
    ></rapi-doc>
  </body>
</html>
""")


@app.get("/", tags=["meta"], dependencies=[Depends(require_api_key)])
def root():
    """List all available table endpoints."""
    conn = get_conn()
    try:
        tables = get_tables(conn)
    finally:
        conn.close()
    return {
        "tables": tables,
        "endpoints": [f"/tables/{t}" for t in tables],
    }


@app.get("/tables", tags=["meta"], dependencies=[Depends(require_api_key)])
def list_tables():
    """Return all tables with their column definitions."""
    conn = get_conn()
    try:
        tables = get_tables(conn)
        result = {}
        for t in tables:
            result[t] = get_columns(conn, t)
    finally:
        conn.close()
    return result


@app.get("/tables/{table}", tags=["data"], dependencies=[Depends(require_api_key)])
def read_table(
    table: str,
    limit: int = Query(100, ge=1, le=10000, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
) -> Any:
    """Return rows from a table with optional pagination."""
    conn = get_conn()
    try:
        tables = get_tables(conn)
        if table not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table}' not found")
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f'SELECT * FROM "{table}" LIMIT %s OFFSET %s',
                (limit, offset),
            )
            rows = cur.fetchall()
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            total = cur.fetchone()["count"]
    finally:
        conn.close()

    return {
        "table": table,
        "total": total,
        "limit": limit,
        "offset": offset,
        "rows": [dict(r) for r in rows],
    }


@app.get("/tables/{table}/columns", tags=["meta"], dependencies=[Depends(require_api_key)])
def table_columns(table: str):
    """Return column definitions for a specific table."""
    conn = get_conn()
    try:
        tables = get_tables(conn)
        if table not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table}' not found")
        columns = get_columns(conn, table)
    finally:
        conn.close()
    return {"table": table, "columns": columns}


@app.get("/tables/{table}/{row_id}", tags=["data"], dependencies=[Depends(require_api_key)])
def read_row(table: str, row_id: str) -> Any:
    """Fetch a single row by its primary key value (assumes 'id' column)."""
    conn = get_conn()
    try:
        tables = get_tables(conn)
        if table not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table}' not found")

        cols = [c["name"] for c in get_columns(conn, table)]
        if "id" not in cols:
            raise HTTPException(
                status_code=400,
                detail=f"Table '{table}' has no 'id' column. Use GET /tables/{table} instead.",
            )

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f'SELECT * FROM "{table}" WHERE id = %s',
                (row_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Row with id={row_id} not found in '{table}'")
    return dict(row)

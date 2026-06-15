from fastapi import FastAPI
from contextlib import asynccontextmanager
import duckdb
import os
from pathlib import Path

DB_PATH = os.environ.get(
    "METROLOGY_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "db" / "metrology.duckdb")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = duckdb.connect(DB_PATH, read_only=True)
    yield
    app.state.db.close()

app = FastAPI(
    title="Metrology QC & Traceability API",
    description="REST API over the Gold layer of the Metrology QC pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

from routers import instruments, trends, uncertainty
app.include_router(instruments.router)
app.include_router(trends.router)
app.include_router(uncertainty.router)

@app.get("/health")
def health():
    return {"status": "ok"}
"""FastAPI entrypoint. Skeleton — routes added in feature commits."""
from fastapi import FastAPI

app = FastAPI(title="Paczkomat Atlas API", version="0.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

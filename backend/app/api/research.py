"""Serves the aggregate evaluation results (JSON files written by the evaluation CLIs) to the research page.

Only numbers computed by the project's own scripts are served; nothing here is hand-typed. The raw datasets
are never exposed: these files hold aggregate metrics only.
"""
import json

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/research")


@router.get("/results")
def results() -> dict:
    out = []
    d = settings.results_dir
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and "kind" in doc and "data" in doc:
                out.append({"id": f.stem, **doc})
        except (OSError, json.JSONDecodeError):
            continue  # a malformed file must not break the page
    return {"results": out, "note": "Aggregate metrics produced by the project's evaluation scripts. Preliminary, non-clinical."}

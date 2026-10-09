"""FastAPI server exposing DQ Validator pipeline endpoints."""
from pathlib import Path
from typing import Dict, Optional, List
import logging
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from data_io.db_helpers import read_sample_policy_data, read_guidewire_cleansing_rules
from data_io.config_loader import get_config
from assessment_first_pipeline import DQAssessmentFirst

logger = logging.getLogger("fastapi_server")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="DQ Validator API",
    description="API endpoints for data quality assessment and cleansing.",
    version="0.1.0"
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


class AssessmentRequest(BaseModel):
    custom_rules: Optional[Dict[str, str]] = Field(
        None,
        description="Optional user-defined cleansing rules mapping column names to rule text"
    )
    fast_mode: Optional[bool] = Field(False, description="Skip LLM-heavy analysis where supported")


class CleanRequest(BaseModel):
    custom_rules: Optional[Dict[str, str]] = Field(
        None,
        description="Optional user-defined cleansing rules mapping column names to rule text"
    )
    skip_llm_guidance: Optional[bool] = Field(
        False,
        description="Skip LLM-guided transformation generation and use heuristics only"
    )
    dedup_method: Optional[str] = Field(
        "keep-first",
        regex="^(keep-first|keep-last|remove-all)$",
        description="Deduplication strategy"
    )
    preview_limit: Optional[int] = Field(20, description="Max number of preview rows in response")


def _load_preview(df, limit: int = 20) -> List[Dict[str, object]]:
    return df.head(limit).to_dict(orient="records")


def _latest_file(pattern: str) -> Optional[Path]:
    files = sorted(OUTPUT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "dq-validator", "mode": get_config().get_mode()}


@app.get("/data")
async def get_data_preview(limit: int = 100):
    try:
        df = read_sample_policy_data(limit=limit)
        if df is None or df.empty:
            raise ValueError("No sample data available")
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "preview": _load_preview(df, min(limit, 20))
        }
    except Exception as exc:
        logger.exception("Failed to read sample data")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/rules")
async def get_rules():
    try:
        df = read_guidewire_cleansing_rules()
        if df is None or df.empty:
            raise ValueError("No cleansing rules available")
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "rules": df.to_dict(orient="records")
        }
    except Exception as exc:
        logger.exception("Failed to read cleansing rules")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/assessment")
async def run_assessment(request: AssessmentRequest):
    pipeline = DQAssessmentFirst()
    try:
        pipeline.fast_mode = bool(request.fast_mode)
        pipeline.load_data()
        pipeline.load_and_interpret_rules(request.custom_rules)
        pipeline.profile_data()
        pipeline.detect_violations()
        report = pipeline.generate_assessment_report()
        return report
    except Exception as exc:
        logger.exception("Assessment failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/clean")
async def run_clean(request: CleanRequest):
    pipeline = DQAssessmentFirst()
    try:
        pipeline.load_data()
        pipeline.load_and_interpret_rules(request.custom_rules)
        pipeline.profile_data()
        pipeline.detect_violations()
        cleaned_df = pipeline.perform_cleansing(
            skip_llm_guidance=request.skip_llm_guidance,
            dedup_method=request.dedup_method or "keep-first"
        )
        latest_cleaned = _latest_file("Sample_Policy_Data_CLEANED_*.csv")
        return {
            "status": "success",
            "rows": len(cleaned_df),
            "dedup_method": request.dedup_method,
            "preview": _load_preview(cleaned_df, request.preview_limit or 20),
            "download_path": str(latest_cleaned.name) if latest_cleaned else None
        }
    except Exception as exc:
        logger.exception("Cleansing failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/download_cleaned")
async def download_cleaned():
    latest_cleaned = _latest_file("Sample_Policy_Data_CLEANED_*.csv")
    if latest_cleaned is None:
        raise HTTPException(status_code=404, detail="No cleaned output file found")
    return FileResponse(latest_cleaned, media_type="text/csv", filename=latest_cleaned.name)


@app.get("/latest_assessment")
async def latest_assessment():
    latest_report = _latest_file("Assessment_Report_*.json")
    if latest_report is None:
        raise HTTPException(status_code=404, detail="No assessment report found")
    try:
        with latest_report.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        logger.exception("Failed to read latest assessment report")
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_server:app", host="0.0.0.0", port=8000, reload=True)

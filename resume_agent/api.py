import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from resume_agent.config import settings
from resume_agent.pipeline import run_pipeline

app = FastAPI(title="Resume Agent API")

# Single-user deployment: any origin may call this from a UI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/generate-resume")
async def generate_resume(jd_text: str | None = Form(default=None), jd_file: UploadFile | None = File(default=None)):
    if not jd_text and not jd_file:
        raise HTTPException(status_code=400, detail="Provide either jd_text or jd_file")

    if jd_file is not None:
        suffix = Path(jd_file.filename or "jd.txt").suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await jd_file.read())
            jd_source = tmp.name
    else:
        jd_source = jd_text

    try:
        result = run_pipeline(jd_source)
    finally:
        if jd_file is not None:
            Path(jd_source).unlink(missing_ok=True)

    response = {
        "job_role_name": result.get("job_role_name"),
        "ats_report": result["ats_report"].model_dump(),
        "jd_match_status": result["jd_match_status"].model_dump(),
    }

    if result["jd_match_status"].matched:
        json_path = Path(result["json_path"])
        docx_path = Path(result["docx_path"])
        response["resume"] = result["resume"].model_dump()
        response["json_filename"] = json_path.name
        response["docx_filename"] = docx_path.name

    return response


@app.get("/download/{filename}")
def download(filename: str):
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = Path(settings.output_dir) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=filename)

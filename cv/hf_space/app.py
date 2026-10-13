import base64
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from cv.flame_cv import PIPELINE_VERSION, CVConfig, CVError, analyze_image

app = FastAPI(title="Flame CV inference", docs_url=None, redoc_url=None)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000


@app.get("/health")
def health():
    return {"status": "up", "pipeline": PIPELINE_VERSION}


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    mm_per_pixel: float | None = Form(default=None, gt=0),
):
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Only JPEG and PNG images are supported.")
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds the 10 MiB upload limit.")

    suffix = ".png" if image.content_type == "image/png" else ".jpg"
    try:
        with tempfile.TemporaryDirectory(prefix="flame-hf-cv-") as directory:
            root = Path(directory)
            input_path = root / f"input{suffix}"
            input_path.write_bytes(content)
            analysis = analyze_image(
                {
                    "imagePath": str(input_path),
                    "imageId": "hf-space-inference",
                    "metadata": {"mmPerPixel": mm_per_pixel},
                },
                root / "processed",
                root / "masks",
                cfg=CVConfig(max_file_bytes=MAX_IMAGE_BYTES, max_pixels=MAX_IMAGE_PIXELS),
            )
            artifact_paths = {
                "preprocessed": analysis["preprocessing"].get("derivedUri"),
                "mask": analysis["segmentation"].get("maskUri"),
                "overlay": analysis["segmentation"].get("overlayArtifactUri"),
            }
            artifacts = {
                name: base64.b64encode(Path(path).read_bytes()).decode("ascii")
                for name, path in artifact_paths.items()
                if path and Path(path).is_file()
            }
            analysis["preprocessing"]["derivedUri"] = None
            analysis["provenance"]["inputUri"] = "uploaded-image"
            analysis["segmentation"]["maskUri"] = None
            analysis["segmentation"]["overlayArtifactUri"] = None
            return JSONResponse({"analysis": analysis, "artifacts": artifacts})
    except CVError as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc

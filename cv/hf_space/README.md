---
title: Flame CV Inference
sdk: docker
app_port: 7860
---

# Flame CV inference Space

This Space serves the existing versioned `cv/flame_cv.py` image-analysis pipeline
through `POST /api/analyze`. It accepts JPEG/PNG multipart uploads (10 MiB maximum)
and returns the analysis JSON plus base64-encoded preprocessed, mask, and overlay
artifacts. `GET /health` is available for readiness checks.

To create a dedicated Hugging Face Space, copy this directory's `README.md`,
`app.py`, `Dockerfile`, and `requirements.txt` to the Space repository root.
Also copy the project's `cv/flame_cv.py` to `cv/flame_cv.py` and `cv/configs/camera_profiles.json`
to `cv/configs/camera_profiles.json` in that repository (the `camera_profile` form field reads it).
Keep the Space private when requests or uploaded images should not be publicly
accessible. Use the Space's read-scoped Hugging Face token as `FLAME_CV_HF_TOKEN`
in the Flame worker environment.

This is a separate inference service; it does not replace or modify any LLM
Space. The API worker can call this service with `FLAME_CV_PROVIDER=hf_space`.
LLM serving and routing remain configured independently.

# Audio transcription for video analyses

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Current, optional, off by default | 1.0.0 | 2026-11-13 | P3-7, Princess roadmap §audio scope | `cv/audio_extraction.py`, `ai/providers/local/faster_whisper_transcription.py`, `apps/api/flame_api/audio_transcript.py`, `apps/api/flame_api/worker.py` |

## Why this exists

The earlier audit decided audio should not be built because "no scientific audio signal was identified". That was an assumption: nobody had decoded the audio. We did, on the 17 NASA BASS-II videos (`PSI-25`):

- **All 17 files have an AAC audio track** (48 kHz stereo).
- **11 carry real, intermittent sound** (loudest second between -33 and -47 dBFS, peaks -12 to -29 dBFS). The audio is **operator speech**: crew and ground controllers talking about ignition attempts ("it immediately went out", "since we had no flame"), fan changes ("fan to zero", "fan to max") and procedure.
- **6 are silent** (loudest second at or below -68 dBFS, peaks below -57 dBFS): `F4`, `F4_2ND_VIEW`, `M10_2ND_VIEW`, `P12`, `T25_2ND_VIEW`, `O1`. Three of the four second-view cameras are in this group.

That speech states things the BASS-II tables do not: the tables have **no outcome columns** (no spread rate, no extinction flag; `docs/data/COMBUSTION_DATASET_ANALYSIS.md` §3.2), and flow velocity is "null until calibrated". It is context for those gaps, not a replacement for measuring them.

## What it does

When `FLAME_TRANSCRIPTION_ENABLED=true`, `process_video_analysis` runs one more step after the frame pipeline:

1. `cv/audio_extraction.py` decodes the first audio stream with PyAV (no `ffmpeg` binary needed) to 16 kHz mono and measures it.
2. If the loudest one-second window is at or below **-55 dBFS** the track is `silent` and no model runs. This matters: Whisper invents text on silence. The threshold sits in a wide gap between the silent clips (at or below -68 dBFS) and the clips with speech (above -47 dBFS).
3. Otherwise the router's `speech.transcribe` task sends the WAV to the local `faster_whisper` provider (`ai/providers/local/faster_whisper_transcription.py`): CPU, int8, VAD-filtered, beam 1.
4. The result is stored as `result.audio` on the analysis (contract 0.7.0, `VideoAudioTranscript`).

It is **local only** (audio never leaves the machine) and **never fails the video job**: a missing model, an undecodable track or a provider crash gives `audio.status = "unavailable"` with a `failure_code`, and the video result is untouched.

| `audio.status` | Meaning |
|---|---|
| `transcribed` | Speech found; `segments[]` filled. |
| `no_speech` | Audible, but the model found no speech (noise). |
| `silent` | Track present, loudest second <= -55 dBFS. No model ran. |
| `no_audio_track` | The file has no audio stream. |
| `unavailable` | Could not run; see `failure_code` (`model_missing`, `decode_failed`, `no_provider`, `transcription_failed`). |

## Turning it on

```bash
python -m ai.providers.local.faster_whisper_transcription prepare --cache-dir <dir>   # online, once; about 480 MB
python -m ai.providers.local.faster_whisper_transcription verify  --cache-dir <dir>   # offline check, prints the sha256
```

```bash
FLAME_TRANSCRIPTION_ENABLED=true
FLAME_TRANSCRIPTION_MODEL=small            # tiny, base, small, medium...; small is what was evaluated
FLAME_TRANSCRIPTION_CACHE_DIR=<dir>        # falls back to FLAME_EMBEDDING_CACHE_DIR, then the Hugging Face default
```

When the effective execution mode is `offline_only` the provider is cache-only: a model that is not cached is `model_missing`, never a download.

Measured on this machine (CPU): a 117 s clip transcribed in about 22 s; a silent 208 s clip was skipped in 2 s.

## What it is not

- **Not evidence and not a measurement.** `classification` is always `machine_transcribed`. No evidence kind, observation or warning code was added (those are fixed lists in the contract), and AI interpretation and AURA do not read it. Showing it in the UI, or turning phrases into outcome labels, is a separate decision that needs human review.
- **Not accurate.** Whisper `small` mis-heard "igniter" as "night" and "fan to max" as "Fanta max". Timestamps are approximate to a few seconds because VAD merges speech into long chunks.
- **Untrusted text.** It is free text from outside the system (requirements SR-1). Treat it like any other external text.
- **Not validated at scale.** 4 of the 11 audible clips (`T10`, `F3`, `F1`, `B1`) were transcribed and skimmed in the session that built this; the other 7 were not transcribed. **No transcript has been checked against the audio by ear.**
- **Not in the web UI.** `apps/web` does not render `result.audio` yet.

## Tests

- `tests/cv/test_audio_extraction.py`: tone, silence, a faint hum, AAC in MP4, video without audio, a non-media file.
- `tests/unit/test_transcription_provider.py`: contract, offline `model_missing` without a download, segment mapping, language pass-through, routing; one test uses the real cached model and skips when it is absent.
- `apps/api/tests/test_audio_transcript.py`: every status, the never-raises rule, and conformance to `VideoAudioTranscript` in `openapi.json`.
- `apps/api/tests/test_video_analysis.py`: the real worker on an H.264 + AAC clip (built with PyAV) with transcription enabled, provider missing, and disabled.

## Open items

- Review and sign off `faster_whisper:small` in the model registry (status is `candidate`).
- Transcribe the other 7 audible clips and check the speech by ear before anyone uses it as a label.
- Decide whether `result.audio` is shown in the dashboard, and whether a reviewed transcript becomes `source_evidence`.
- Run the AURA Link 2 dry run against contract 0.7.0 (the change is additive; the pinned AURA revision was not available in this session).

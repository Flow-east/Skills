# Spoken-video editing (`koubo-editing`)

[简体中文](README.zh-CN.md)

A Chinese-language talking-head editing skill: assess the spoken content first, then decide on structure, opening hook, semantic cuts, captions, camera rhythm, sound effects, transitions, optional stickers, and privacy masking before rendering a **video with audio**. It keeps a plan, subtitles, creative brief, and QA report; it does not equate technical checks with human review.

The package includes **54 reference-led calibration templates** and 74 provenance-recorded CC0 sound-effect choices. These are preview-grade implementations awaiting individual aesthetic acceptance, **not** official templates or a 1:1 clone of any editing product. The underlying reference videos, user footage, transcripts, personal credentials, and speech models are not included.

## Install

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R koubo-editing "${CODEX_HOME:-$HOME/.codex}/skills/koubo-editing"
```

Ask the agent in Chinese to edit a spoken video, or explicitly invoke `$koubo-editing`. Provide a local video. Python 3, Pillow, NumPy, and FFmpeg/ffprobe are required; choose and install an optional speech-recognition backend/model separately. See `SKILL.md`, `references/runtime.md`, and `references/plan-format.md`. Optional external image generation requires its own installed skill and explicit permission to send material and incur charges.

## Validate

```bash
python3 -m unittest discover -s koubo-editing/tests -v
python3 koubo-editing/scripts/template_library.py validate
python3 koubo-editing/tests/smoke_test.py
```

Original code/docs are MIT-licensed. Bundled font licenses (SIL OFL) and sound effects (CC0 1.0, with per-item provenance) are **not** relicensed by the repository MIT license. See [third-party notices](THIRD_PARTY_NOTICES.md).

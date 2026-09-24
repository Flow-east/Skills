# Spoken-video editing · v0.3.0

**English** | [简体中文](README.zh-CN.md)

A skill for editing Chinese talking-head videos from content review to an audio-backed final cut. It plans the narrative first, then applies a visual style, renders, and verifies the result.

## Features

- Local speech transcription with word-level timestamps; semantic removal of repetition, slips, and pauses without clipping sentence endings.
- Opening and content structure, camera rhythm, caption hierarchy, keyword stickers, sound effects, transitions, and privacy masking.
- 54 visual templates and 74 optional sound effects. Illustrative stickers can use any available, authorized image-generation tool; no specific provider is required.
- Audio-backed MP4, reusable edit plan, SRT subtitles, creative brief, and QA report.

## Install

From the repository root:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R koubo-editing "${CODEX_HOME:-$HOME/.codex}/skills/koubo-editing"
```

Alternatively, give this directory to a compatible agent or run `npx skills add Flow-east/Skills --skill koubo-editing`.

## Use

Provide a readable local spoken-video file and ask the agent to edit it, or invoke `$koubo-editing`. The workflow checks spoken content and structure before creating a brief and rendering; analysis-only requests do not trigger a render. External image-generation services and paid calls require an available tool and separate authorization.

See [`references/quickstart.md`](references/quickstart.md) for a quick preview, [`references/plan-format.md`](references/plan-format.md) for the plan schema, and [`references/template-library.md`](references/template-library.md) for template selection and limits. Detailed working references are in Chinese because the editing workflow targets Chinese speech.

## Requirements and validation

Python 3, Pillow, NumPy, and FFmpeg/ffprobe are required. Configure a local speech-recognition backend and model separately as described in [`references/runtime.md`](references/runtime.md).

```bash
python3 -m unittest discover -s koubo-editing/tests -v
python3 koubo-editing/scripts/template_library.py validate
python3 koubo-editing/tests/smoke_test.py
```

## License

Original code and documentation use the repository MIT license. Bundled fonts and sound effects keep their own licenses and provenance; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

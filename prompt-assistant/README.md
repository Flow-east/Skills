# Prompt Assistant

**Turn an idea into a usable prompt, and keep the experience worth reusing.**

[简体中文 / Full guide](README.zh-CN.md) · v0.1.0 · MIT

A personal prompt assistant for agents supporting the Agent Skills folder format. It helps clarify an idea, refine an existing prompt, diagnose an unsatisfactory result, or package conversation context for another AI tool. Chinese-first instructions; the agent should use the user's language.

The Skill includes scoped personal preferences, versioned prompt cases, outcome evidence, project context, learning records, and reusable methods. Personal data lives outside the installed Skill, so updating the public package preserves the user's accumulation.

## Start

Ask a compatible agent:

```text
Install this Skill:
https://github.com/Flow-east/Skills/tree/main/prompt-assistant
```

Then try:

```text
Use $prompt-assistant to turn this idea into a prompt for an image tool. Help me work out the details that matter.
```

```text
Package the decisions from our conversation into a standalone prompt for another agent. Preserve my argument and list any files I need to attach.
```

```text
The second version kept the character consistent, but the camera moved incorrectly. Help me diagnose it and remember the actual outcome.
```

Install the complete `prompt-assistant` folder, including `scripts/`, `references/`, and `agents/`. A pinned release uses the tag `prompt-assistant-v0.1.0`. The [Chinese guide](README.zh-CN.md#安装) includes a first-install command for Codex. Host discovery and automatic invocation vary by client.

## How learning works

- A prompt the user accepts is distinct from an output that actually worked. Every result records whether it was user-reported or observed.
- Preferences have project, scenario and tool scopes. A one-off request does not become a global rule. Current instructions override stored defaults.
- Prompt revisions are separate cases linked to one task. Feedback targets a specific version.
- Reusable personal methods begin as candidates. Adoption requires useful comparisons from two independent tasks; known counterexamples need explicit resolution. This is an engineering gate, not statistical proof of improvement.
- Teaching is optional and tied to the current task. Explaining a concept is not evidence the user has mastered it.
- Corrections, scope changes, history, rollback, export and forgetting are supported through natural-language requests.

Stable workflows and sourced knowledge are maintained by the author. The Skill does not rewrite its public instructions after each conversation. References load on demand.

## Runtime and data

Full persistence requires **Python 3.9+** and filesystem access. The SQLite helper uses only the standard library; no additional model API, vector service, or background process is needed. Without persistent tools, the Skill still works within the current conversation.

Default data: `~/.local/share/prompt-assistant/` on macOS/Linux (honoring `XDG_DATA_HOME`), or `%LOCALAPPDATA%/prompt-assistant/` on Windows. Override with `PROMPT_ASSISTANT_HOME` or the script's `--data-dir` option. The installed Skill directory is rejected as a data location.

Selective local memory is on by default, with a brief first-use disclosure. Say “don't remember this session,” “turn memory off,” “show my preferences,” “forget this case,” or “export my memory.” Memory-off stops learning writes and contextual recall while keeping explicit inspection, export and deletion available.

Local storage is not encryption or an offline-model guarantee: retrieved records enter the host agent's context. The helper does not access other apps or automatically see downstream outputs. Forgetting removes linked database content, not existing exports, OS backups, external images, or host conversation history. Import supports an empty database with the same schema; methods require revalidation after transfer.

## Validation

From the repository root:

```bash
python3 -m unittest discover -s tests/prompt-assistant -v
```

The tests verify storage and multi-session behavior. They do not establish improved prompt quality across models. See the [evaluation cases](https://github.com/Flow-east/Skills/tree/main/tests/prompt-assistant) for a reproducible behavioral evaluation plan.

Agent entry point: [SKILL.md](SKILL.md). Runtime operations: [memory-operations.md](references/memory-operations.md). Original sources and maintenance rules: [sources.md](references/sources.md). Licensed under [MIT](LICENSE).

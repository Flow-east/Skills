# Flow-east Skills

**English** | [简体中文](README.zh-CN.md)

Reusable skills for Codex and other coding agents that support the Agent Skills folder format.

## Skills

| Skill | Release | What it does | Best for | Details |
| --- | --- | --- | --- | --- |
| `mac-mail-management` | [v0.1.0](https://github.com/Flow-east/Skills/blob/mac-mail-management-v0.1.0/mac-mail-management/README.md) | Manages configured Apple Mail accounts, drafts and replies with local attachments, and authorized submissions with duplicate prevention. | QQ/Gmail inbox triage, résumé applications, and scheduled mail workflows on a Mac. | [English guide](mac-mail-management/README.md) · [中文说明](mac-mail-management/README.zh-CN.md) |
| `prompt-assistant` | [v0.1.0](https://github.com/Flow-east/Skills/blob/prompt-assistant-v0.1.0/prompt-assistant/README.md) | Creates and diagnoses prompts while accumulating scoped preferences, cases, outcome evidence and validated personal methods. | Portable prompts, image/video instructions, iterative refinement, and learning from actual use. | [English guide](prompt-assistant/README.md) · [中文说明](prompt-assistant/README.zh-CN.md) |
| `feishu-doc-permission` | [v0.1.0](https://github.com/Flow-east/Skills/blob/feishu-doc-permission-v0.1.0/feishu-doc-permission/README.md) | Validates document content before a Feishu write and grants collaborators edit access after creation. | Feishu document automation that must avoid empty documents and missing permissions. | [English guide](feishu-doc-permission/README.md) |
| `live-selling-script` | [v0.1.0](https://github.com/Flow-east/Skills/blob/live-selling-script-v0.1.0/live-selling-script/README.md) | Co-creates, reviews, and rewrites evidence-grounded Chinese livestream sales scripts. | Livestream scripts, product demos, objection handling, platform adaptation, and transcript-based rewriting. | [English guide](live-selling-script/README.md) |
| `vpn-git-handoff` | [v0.2.0](https://github.com/Flow-east/Skills/blob/vpn-git-handoff-v0.2.0/vpn-git-handoff/README.md) | Coordinates safe Git handoffs and can optionally open a system terminal when a required VPN disconnects the coding agent. | Human-operated VPN windows for fetch, sync, push, clone, and failure recovery. | [English guide](vpn-git-handoff/README.md) |
| `koubo-editing` | [v0.3.0](https://github.com/Flow-east/Skills/blob/koubo-editing-v0.3.0/koubo-editing/README.md) | Reviews Chinese speech, plans semantic cuts and visual/audio treatment, and renders a video with audio. | Chinese talking-head video editing with reusable styles. | [English guide](koubo-editing/README.md) · [中文说明](koubo-editing/README.zh-CN.md) |

Each skill is self-contained and versioned independently with Semantic Versioning. “First published” dates link to the earliest repository commit that shipped the skill; Git tags identify version snapshots. Start with a skill's README for human-facing guidance; the agent loads `SKILL.md` and any relevant resources when the skill applies.

## Install

Choose one of the skill names listed above.

### Ask a compatible agent

Give your agent the skill's GitHub URL, for example:

```text
Install this skill:
https://github.com/Flow-east/Skills/tree/main/vpn-git-handoff
```

### Skills CLI

If your environment provides a compatible Skills CLI:

```bash
npx skills add Flow-east/Skills --skill vpn-git-handoff
```

Replace `vpn-git-handoff` with any skill name from the table above.

### Manual installation for Codex

```bash
git clone https://github.com/Flow-east/Skills.git floweast-skills
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R floweast-skills/vpn-git-handoff \
  "${CODEX_HOME:-$HOME/.codex}/skills/vpn-git-handoff"
```

When installing another skill, replace the source and destination folder names in the `cp` command with the same skill name.

Other agents can use the same skill folder when they support `SKILL.md`; agent-specific metadata such as `agents/openai.yaml` is optional outside Codex.

## Development and validation

Validate every skill with the Skill Creator bundled with Codex:

```bash
for skill in feishu-doc-permission live-selling-script vpn-git-handoff prompt-assistant mac-mail-management koubo-editing; do
  python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

Run the repository's unit tests:

```bash
python3 -m unittest discover -s tests/live-selling-script -v
python3 -m unittest discover -s tests/prompt-assistant -v
python3 -m unittest discover -s mac-mail-management/tests -v
python3 -m unittest discover -s koubo-editing/tests -v
node mac-mail-management/tests/test_driver.js
```

## License

Unless otherwise noted (including bundled fonts and sound effects listed in `koubo-editing/THIRD_PARTY_NOTICES.md`), this repository is available under the [MIT License](LICENSE).

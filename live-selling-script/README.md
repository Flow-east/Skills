# Live Selling Script

**English** | [简体中文](README.zh-CN.md) · [← All Skills](../README.md)

Current release: [v0.1.0](https://github.com/Flow-east/Skills/blob/live-selling-script-v0.1.0/live-selling-script/README.md) · First published: [2026-07-12](https://github.com/Flow-east/Skills/commit/2e68ab76dc927a3f9459569eb060a0873b9922da)

`live-selling-script` is an Agent Skill for co-creating, drafting, reviewing, and rewriting Chinese livestream sales scripts. It grounds the script in product facts, audience context, visible evidence, the host's natural voice, and a realistic next action instead of forcing every product into one sales template.

## When to use it

- Create a livestream script from product pages, screenshots, briefs, past scripts, or other source material.
- Adapt a product pitch for WeChat Channels, Douyin, Taobao Live, Kuaishou, or a presentation and competition setting.
- Review an existing script for unsupported claims, weak evidence, awkward written language, generic AI phrasing, or a mismatched call to action.
- Separate a faithful video or audio transcript from later structure analysis and rewriting.
- Produce a quick draft when the product facts are already complete, while keeping assumptions and unknowns visible.

The Skill can produce fact cards, audience and pain-point maps, evidence and objection maps, six-step outlines, 5–10 minute reusable product loops, host and production cues, interaction branches, and focused audit reports.

## How it works

The default co-creation flow is progressive:

```text
Product facts
→ Audience and pain points
→ Platform and host voice
→ Evidence, demonstrations, objections, and offer terms
→ Six-step structure
→ Spoken script
→ Fact, delivery, and conversion review
```

The final script uses a six-step audience journey:

```text
Audience entry
→ Pain-point trust
→ Useful method
→ Interactive confirmation
→ Pain-point extension
→ Clear next action
```

This is a reasoning structure, not six fixed blocks of copy. The emphasis, evidence, pace, and next action change with the product, platform, audience, and purchase decision.

Four working modes keep the process proportional to the request:

| Mode | Best for |
| --- | --- |
| Co-creation | Starting from scratch, incomplete information, or products that need careful positioning |
| Quick draft | Complete product facts and an explicit request for an immediate script |
| Audit | Reviewing claims, evidence, structure, spoken delivery, and conversion logic before rewriting |
| Transcript organization | Preserving confirmed speech and unclear passages before analysis or editing |

## Scope and boundaries

- Product-specific prices, inventory, policies, results, and scarcity are never filled in from category convention.
- Unsupported facts stay marked as assumptions or placeholders; important product claims should point to visible or verifiable evidence.
- The Skill does not manufacture testimonials, orders, comments, countdowns, or urgency.
- A product capability is not rewritten as a guaranteed user outcome.
- If the user asks only for an audit, faithful transcript, or another limited deliverable, the Skill stops at that boundary.
- Platform rules change. The included baselines and linter do not replace current official-rule checks, legal advice, or professional compliance review.

## Install

Ask Codex to install the Skill:

```text
Please install this skill:
https://github.com/Flow-east/Skills/tree/main/live-selling-script
```

Or use a compatible Skills CLI:

```bash
npx skills add Flow-east/Skills --skill live-selling-script
```

For a manual Codex installation from a repository checkout, copy the whole directory so its relative `references/` and `scripts/` paths remain intact:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R live-selling-script "${CODEX_HOME:-$HOME/.codex}/skills/live-selling-script"
```

## Quick start

```text
Use $live-selling-script to co-create a Chinese livestream sales script for my course. Review my existing materials first, then tell me what must be confirmed before drafting.
```

Natural-language requests work as well when the agent supports automatic Skill discovery.

## Validate a script

The bundled linter uses only the Python standard library. From the repository root:

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md
```

Use machine-readable output or strict mode when needed:

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md --json
python3 live-selling-script/scripts/lint_script.py path/to/script.md --strict
```

It flags common risks such as absolute or result guarantees, unverified scarcity and numbers, price anchors, command-style hooks, unresolved placeholders, and unusually long spoken lines. In strict mode, high-risk findings or unresolved placeholders return exit code `1`; unreadable input returns `2`. Findings are prompts for human review, not proof of compliance.

Run its unit tests with:

```bash
python3 -m unittest discover -s tests/live-selling-script -v
```

## Detailed guides

- [Agent execution instructions](SKILL.md)
- [Six-step loop](references/six-step-loop.md)
- [Audience and pain-point research](references/discovery-routes.md)
- [Platform and scenario baselines](references/platform-baselines.md)
- [Product facts, evidence, and risk boundaries](references/fact-evidence-compliance.md)
- [Spoken style and audience experience](references/spoken-style.md)
- [Stage outputs and delivery formats](references/output-contracts.md)

## Method sources

The Skill draws on general practices from public livestream-commerce agents and skills, including host coaching, platform adaptation, interaction, FAQ handling, compliance awareness, and time-structured scripts:

- [Livestream Commerce Coach](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-livestream-commerce-coach.md)
- [China E-Commerce Operator](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-china-ecommerce-operator.md)
- [marketing-ecommerce-operator SKILL.md](https://github.com/treexxx/agent_skill/blob/main/skills/marketing-ecommerce-operator/SKILL.md)
- [TK Livestream Script Generator](https://xiaping.coze.com/skill/78a4146b-cfdd-4fd4-9ff0-9223b4b46f95)

Its own synthesis centers on the six-step loop, staged co-creation, product facts before marketing claims, evidence before adjectives, and spoken-language review from the audience's point of view. It intentionally avoids pressure-selling patterns, fabricated scarcity, and unverified industry statistics.

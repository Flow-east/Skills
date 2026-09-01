# VPN Git Handoff

**English** | [简体中文](README.zh-CN.md) · [← All Skills](../README.md)

Current release: [v0.1.0](https://github.com/Flow-east/Skills/blob/vpn-git-handoff-v0.1.0/vpn-git-handoff/README.md) · First published: [2026-09-01](https://github.com/Flow-east/Skills/commit/ea20e0c550eadd80f81705be4567ff7a499065f4)

An agent-neutral skill for Git remotes that are reachable only through a full-tunnel VPN that disconnects the coding agent.

The workflow treats the network switch as a hard responsibility boundary:

```text
Agent connected
  inspect → decide → test → prepare exact handoff card
                         ↓
Human on VPN
  switch network → run listed remote commands → preserve output
                         ↓
Agent reconnected
  inspect result → integrate locally → test → prepare another card if needed
```

## Supported workflows

- Prepare and publish a local branch.
- Fetch remote state, then let the reconnected agent merge, rebase, or fast-forward safely.
- Clone a VPN-only repository into a verified destination.
- Recover from non-fast-forward, authentication, network, protected-branch, hook, LFS, or submodule failures.
- Generate a repository-specific manual handoff document.

Ordinary `git pull` is intentionally excluded from handoff cards because it combines remote transfer with local integration and may create conflicts while the agent is disconnected.

Push cards name the remote and destination branch explicitly instead of relying on local `push.default` or push-remote configuration.

## Human and agent boundaries

| Coding agent | Human |
| --- | --- |
| Inspect repository and choose Git strategy | Connect and disconnect the VPN |
| Complete authorized local edits, tests, commits, merges, and rebases | Run only the exact commands in the card |
| Produce commands, success signals, and stop conditions | Preserve complete terminal output |
| Reconcile results after reconnection | Stop and return when instructed |

The human is never expected to improvise branch strategy, conflict resolution, force push, remote configuration, or credential changes during the disconnected window.

Generating a card does not itself authorize edits or commits, and any card becomes invalid if its verified branch, HEAD, worktree, remote, or target changes.

## Portable package

The core package follows the open Agent Skills folder format:

```text
vpn-git-handoff/
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── references/
│   └── manual-vpn-git-sop.md
└── agents/
    └── openai.yaml
```

`SKILL.md` and `references/` are agent-neutral. `agents/openai.yaml` is optional Codex UI metadata; other skills-compatible agents can ignore it.

## Install

Copy the entire `vpn-git-handoff` directory into the skills directory supported by your coding agent.

For a personal Codex installation:

```bash
cp -R vpn-git-handoff ~/.codex/skills/
```

For an agent that does not discover Agent Skills automatically, provide `SKILL.md` as a reusable instruction file and keep its relative `references/` path intact.

## Use

Explicit invocation where supported:

```text
Use $vpn-git-handoff to prepare the next safe VPN Git handoff for this repository.
```

Natural-language examples:

```text
Prepare this branch so I only need to switch to the VPN and follow your push card.
```

```text
Generate a project-specific VPN Git handoff guide.
```

## Scope and safety

- Works with any VPN-only Git remote, not only GitLab.
- Does not configure VPN clients, proxies, split tunneling, or system routes.
- Does not expose credentials in cards or documentation.
- Does not delegate merge, rebase, conflict, force-push, or remote decisions to the disconnected human.
- Treats merge requests, releases, server pulls, and deployment as separate workflows.

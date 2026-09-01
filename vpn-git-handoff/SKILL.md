---
name: vpn-git-handoff
description: Coordinate safe Git work when a VPN-only remote requires a human network switch that disconnects the coding agent. Use to prepare exact handoff cards for fetch and sync, push, clone, and failure recovery, with local integration and decisions handled by the agent before or after the switch. Do not use to automate VPN changes, bypass network policy, or perform unapproved deployment.
---

# VPN Git Handoff

Use network switching as a hard handoff boundary. The agent plans and verifies the work while connected. The human switches networks, runs the exact remote commands in the handoff card, preserves their output, then returns control to the agent.

Use the user's language for all human-facing output. This workflow applies to any VPN-only Git remote, including self-hosted GitLab, GitHub Enterprise, Bitbucket, Gitea, and plain SSH Git servers.

## Responsibility contract

The agent owns:

- repository inspection and interpretation;
- branch, remote, upstream, and commit decisions;
- local edits, tests, staging, commits, merges, rebases, and conflict resolution when authorized;
- selection and verification of the exact commands placed in a handoff card;
- post-handoff inspection and the decision whether another network window is needed.

Invoking this skill or asking for a handoff card grants no additional mutation authority. Inspect read-only by default; edit, stage, commit, merge, or rebase only when the user's request already authorizes that work.

The human owns:

- connecting to and disconnecting from the required VPN or network;
- running only the commands listed in the current handoff card, in order;
- preserving the complete command output, including errors;
- stopping at the card's success or failure condition and returning to the agent.

During the disconnected network window, do not ask the human to choose a branch strategy, improvise commands, resolve conflicts, edit remotes, change credentials, or decide whether to merge, rebase, reset, or force push.

## Optional system-terminal assistance

When a human-operated network window is required, the agent may help open an external system terminal after the handoff card's commands and stop conditions are finalized and verified, and before the human switches networks. This is a convenience only: opening a terminal grants no authority to run Git commands or perform other mutations. Do not prompt for or open a terminal when no human network step is needed.

Use these preference modes:

- `ask` is the default when no preference is known. Offer four concise choices: open once, always open, not now, or never ask again. Open once and not now leave the mode as `ask`; always open selects `auto-open`; never ask again selects `off`.
- `auto-open` is entered only by explicit opt-in. Open the terminal for each eligible handoff. On the first two successful automatic opens, briefly explain how to disable the behavior; after that, use only a terse success confirmation. Count only opens the agent can verify.
- `off` suppresses both the prompt and automatic opening until the user explicitly changes the preference.

Persist a preference only through a durable preference or memory mechanism already supported by the host. If none is available, say that the choice applies only to the current conversation or session. Never create a preference file or edit repository, Git, shell, or other global configuration unless the user explicitly requests it.

Prefer an external system terminal that remains available when the agent disconnects, while respecting an explicit supported terminal choice. Open push, fetch, and recovery handoffs at the verified repository root; open clone handoffs at the verified parent directory of the destination. Open or focus the terminal only. Never type, paste, preload, or execute the card's commands. Keep the exact numbered commands, including `cd`, in the self-contained handoff card even when the terminal opens at the expected path.

Treat an existing terminal as satisfying the assistance only when the agent can verify that the intended system terminal is open at the correct path. Otherwise use the normal open flow, and never claim that a terminal is open or correctly located without verification. If terminal control is unavailable, denied by a platform permission prompt, or fails, treat the platform result as authoritative, give the human the exact `cd` command, and continue with the handoff rather than blocking it.

## Three-phase protocol

### 1. Agent-connected preparation

Inspect the repository root, current branch, working tree, remotes, upstream, effective push target, latest commit, remote-tracking refs, and any merge, rebase, cherry-pick, or revert already in progress. Complete all authorized local work and proportionate checks. Preserve unrelated user changes.

Do not issue a handoff card from detached HEAD, with unresolved conflicts, or during an unfinished merge, rebase, cherry-pick, or revert unless the agent first resolves that state according to explicit user intent. Never auto-stash, reset, or discard a dirty working tree. Either isolate the authorized change safely and describe remaining local changes, or stop for a decision.

Determine which network operation is actually required. Never claim that remote state is current unless a relevant fetch completed during a recent VPN window.

### 2. Human-operated network window

Produce one self-contained handoff card. After its commands and stop conditions are final, apply any enabled system-terminal assistance, then let the human switch to the required network, execute the card, record the complete result, disconnect the VPN, and return to the agent. Keep this phase limited to simple remote data transfer or remote reference updates with clear stopping conditions. If the branch, HEAD commit, working tree, remote, or target changes after the card is generated, the card is invalid and must be regenerated.

Do not control the VPN, modify system routes or proxies, or assume the agent remains connected during this phase.

### 3. Agent-connected reconciliation

After reconnection, inspect the repository and the preserved output. Perform local integration, conflict resolution, verification, and commit preparation as needed. If a further fetch or push is required, issue a new handoff card rather than asking the human to improvise from the previous one.

## Choose the workflow

### Publish local changes

Prepare the intended commit and verify the local branch, remote, destination branch, upstream, effective push configuration, working tree, and relevant checks. Use an explicit refspec in the card so `push.default`, `branch.pushRemote`, `remote.pushDefault`, or a triangular workflow cannot redirect the push:

```bash
git push <remote> <local-branch>:<remote-branch>
```

For the first publication of a branch, add `-u` only when setting that verified upstream is intended.

If push is rejected with `non-fast-forward` or `fetch first`, the card may direct the human to run `git fetch <remote>` while the VPN is still connected, then stop and return to the agent. Integrate the fetched state only after reconnection.

### Refresh and synchronize remote state

Before issuing the fetch card, identify the remote branch to refresh and the intended post-fetch outcome: update its local branch, create a new branch from it, or integrate it into the current branch. If that outcome is unclear, fetching may proceed safely, but do not mutate local branches until the user confirms the intended result.

Use a fetch handoff:

```bash
git fetch <remote>
```

Do not place ordinary `git pull` in the network handoff. Pull combines remote transfer with merge or rebase and can leave the working tree conflicted while the agent is disconnected.

After reconnection, compare the local branch with its fetched remote-tracking branch. Fast-forward only when valid; when histories diverge, choose merge or rebase according to repository policy and the actual commit relationship. Rerun relevant checks before preparing a later push.

### Clone a repository

Before issuing a clone card, verify the credential-free remote URL and that the destination does not exist or is safely empty. The human performs the exact `git clone` command during the VPN window. After reconnection, inspect the new repository before making changes or installing dependencies. If clone is partial or fails, do not ask the human to delete, overwrite, or retry into the same destination without agent review.

### Recover from failure

- For authentication errors or unexpected credential prompts, preserve the exact error and stop. Diagnose credentials after reconnection without placing secrets in commands, URLs, chat, or documentation.
- For network errors, confirm the VPN is connected and retry once at most if the card explicitly permits it. Otherwise stop.
- For protected-branch, permission, hook, or server-policy rejection, preserve the complete output and stop. Do not bypass policy or silently switch targets.
- For partial clone, fetch, LFS, or submodule failure, treat the operation as incomplete and return to the agent.

## Conditional repository features

Before writing a card, inspect only the features the repository actually uses:

- Git LFS: normal push hooks should upload required objects; do not default to `git lfs push --all`. Treat an LFS upload failure as an overall push failure.
- Submodules: if a superproject commit references a new submodule commit, ensure the submodule commit is remotely reachable first and provide separate, ordered handoffs when necessary.
- Tags: include an exact tag push only when the user explicitly intends to publish that tag. Do not default to `git push --tags`.

Do not use `push --all`, `push --mirror`, force push, hard reset, clean, or destructive recovery as a generic shortcut. Discuss `--force-with-lease` only after the user explicitly requests history replacement and the agent has reviewed the commit relationship.

## Handoff card contract

Every actual handoff card must contain verified values rather than placeholders:

1. Goal of this network window.
2. Preconditions already checked by the agent.
3. When terminal assistance was offered or attempted for this handoff, its status: verified terminal and path, human will open it, or unavailable with the exact `cd` fallback. Omit this field in `off` mode so that opting out remains silent.
4. Absolute repository path or safe clone destination.
5. Exact local branch or commit, remote, and remote destination branch where applicable.
6. Exact numbered commands, including `cd` where applicable.
7. Recognizable success output.
8. Specific failure branches, allowed fallback command if any, and a clear stop condition.
9. Instruction to disconnect the VPN and return the complete result to the agent.

Sanitize remote addresses and quote paths safely for the user's shell. Never expose tokens, passwords, private keys, credential-bearing URLs, or sensitive query parameters. Ask the human to redact any accidentally printed secret before returning output. Make the card usable without access to earlier conversation messages.

## Project documentation

When the user requests a repository-specific manual, read [references/manual-vpn-git-sop.md](references/manual-vpn-git-sop.md). Adapt it using verified repository facts and the user's language, defaulting to `VPN-GIT-HANDOFF.md` rather than a deployment filename. Mark unknown release or deployment details as requiring confirmation instead of inventing them.

A successful Git push confirms only that the remote reference and any required objects were updated. It does not confirm a merge request, release, server pull, or deployment.

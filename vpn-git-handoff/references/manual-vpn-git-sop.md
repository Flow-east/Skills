# Manual VPN Git Handoff SOP Template

Adapt this template using verified repository facts and the user's language. Replace angle-bracket placeholders and remove irrelevant sections. Never record passwords, tokens, private keys, or credential-bearing URLs.

## Working agreement

The coding agent prepares and verifies all local work, decides the Git strategy, and writes each handoff card. After the card is final, the agent may optionally open an external system terminal for the human; it never types, pastes, preloads, or runs the Git commands. The human switches networks, runs the listed commands exactly, preserves their complete output, and switches back. The human does not improvise merge, rebase, reset, remote, credential, or force-push decisions while the agent is disconnected.

## Before connecting the VPN

The agent verifies:

- repository path and intended outcome;
- current branch, remote, and upstream;
- effective push target, including the remote destination branch;
- for fetch workflows, the remote branch to refresh and the intended post-fetch outcome;
- working-tree state and any unfinished Git operation;
- the commit or remote-tracking state relevant to this handoff;
- applicable tests and conditional Git LFS, submodule, or tag requirements;
- exact commands, expected success output, and stop conditions.

## Optional terminal assistance

Terminal assistance happens only after the handoff card's commands and stop conditions are final, and before the human connects the VPN. The default mode is `ask`, with four choices: open once, always open, not now, or never ask again. Always open enables `auto-open`; never ask again enables `off`. On the first two verified automatic opens, the agent includes a brief reminder that the behavior can be disabled; later confirmations stay terse.

Prefer an external system terminal that remains usable while the coding agent is disconnected. Open it at the verified repository root for push, fetch, or recovery, or at the verified parent directory of a clone destination. The agent opens or focuses the terminal only; the handoff card still includes the exact `cd` and Git commands for the human to run.

Persist the preference only when the host already provides durable preference or memory support. Otherwise it applies only to the current conversation or session. Do not create configuration files or change repository, Git, shell, or global settings for this preference. Do not claim that the correct terminal is already open unless that state can be verified. If opening is unsupported, denied by the platform, or fails, use the exact `cd` fallback in the card and continue manually.

## Handoff card

### Goal

<Fetch remote state, push a verified commit, clone a repository, or recover remote state.>

### Preconditions confirmed by the agent

- Repository or destination: `<absolute-path>`
- Branch: `<branch-or-not-applicable>`
- Remote: `<remote-name-and-sanitized-address>`
- Commit: `<short-hash-and-subject-or-not-applicable>`
- Terminal assistance: `<verified terminal and path | human will open | unavailable; use exact cd below | omit this line when mode is off>`
- Card validity: `<branch, HEAD, worktree, remote, and target conditions that must remain unchanged>`

### Human steps

1. Use the verified system terminal and path reported above, or open a terminal if none is reported.
2. Connect the required VPN or network.
3. Run only the numbered commands below, in order. Start with the listed `cd` command even if the terminal appears to be in the correct directory.

```bash
<exact-commands>
```

4. Stop when the success or failure condition below is reached.
5. Preserve the complete terminal output.
6. Disconnect the VPN and return the result to the coding agent.

### Success condition

<Exact recognizable result.>

### Failure and stop conditions

- For an expected non-fast-forward push rejection, run the explicitly listed `git fetch <remote>` fallback if present, then stop.
- For authentication, protected-branch, permission, hook, unexpected credential, LFS, submodule, or repeated network failure, run no additional Git mutation. Preserve the output and stop.
- Never improvise `git pull`, merge, rebase, reset, force push, remote changes, or credential changes.

## After reconnecting the agent

The agent inspects the repository and output, performs any local integration or conflict resolution, reruns relevant checks, and decides whether a new handoff card is required.

## Common card commands

Use only after replacing every placeholder with verified values.

Fetch remote state:

```bash
cd '<absolute-repository-path>'
git fetch <remote>
```

Push to a verified destination branch:

```bash
cd '<absolute-repository-path>'
git push <remote> <local-branch>:<remote-branch>
```

Publish a branch for the first time:

```bash
cd '<absolute-repository-path>'
git push -u <remote> <local-branch>:<remote-branch>
```

Clone:

```bash
cd '<absolute-parent-directory>'
git clone <credential-free-remote-url> '<absolute-destination-path>'
```

Do not use ordinary `git pull` in a handoff card. Fetch during the VPN window, then let the reconnected agent choose and perform the local integration strategy.

If the branch, HEAD commit, working tree, remote, or target changes after this card is generated, discard the card and ask the agent for a new one.

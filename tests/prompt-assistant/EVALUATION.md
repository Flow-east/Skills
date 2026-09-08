# Prompt Assistant evaluation

The CLI suite uses synthetic content and isolated temporary directories. Every command starts a fresh Python process; `test_multi_session_lifecycle` exercises a continuous user's sequence across those process boundaries. It checks persistence mechanics, not whether a language model actually follows the Skill.

```bash
python3 -m unittest discover -s tests/prompt-assistant -v
```

The suite covers scope filtering and conflict precedence, personal-fact evidence requirements, accepted versus actual outcomes, feedback version identity, two-task method adoption, counterexamples, correction/rollback, teaching stages, memory-off, atomic batch/import behavior, export no-clobber, deletion of linked history, Chinese recall budgets, concurrency, and portable restoration. A field-level evidence check cannot prove the evidence is true; model and user review remain necessary.

## Behavioral evaluation

`behavioral-cases.json` contains 15 synthetic host-agent tasks with observable checks. Before changing the workflow, run the relevant cases in a fresh host session with this Skill installed. For meaningful outcome claims, use the actual target tool and preserve its parameters and returned artifact.

1. Record host, model/version, Skill commit, target tool/version, enabled tools and date. Use `PROMPT_ASSISTANT_HOME` pointing to an isolated temporary directory; never seed the author's or another user's memory.
2. Run each task in ordinary language. Seed only the synthetic context named in that case, through the documented CLI where persistent records are required. Keep visible messages, invoked commands and returned artifacts, excluding hidden reasoning and secrets.
3. For each check record `pass/fail/not-observable`, with the exact visible evidence. A missing tool is a capability limitation, not a silently assumed pass.
4. Compare baseline and changed Skill under the same conditions, preferably blinded for final output review. Separate fidelity to intent, usability of the delivered prompt, outcome quality, unnecessary interaction cost and memory correctness. Do not collapse these into an unsupported single quality score.
5. For a claimed reusable method, compare downstream outputs, preserve unsuccessful cases, and repeat on an independent task. Text approval alone cannot establish outcome improvement.

No host-agent benchmark or live image/video quality improvement is claimed by the initial release. The supplied cases are an evaluation specification; deterministic CLI tests are executed separately and reported as such.

## Release checks

- Validate Skill frontmatter and every local resource link.
- Execute the CLI suite on the minimum supported Python; smoke-check the bundled runtime when available.
- Inspect package contents for private data, temporary exports, caches and unresolved placeholders.
- Ensure imported methods require new-environment validation and that known counterexamples cannot be silently bypassed.
- Verify a clean install can locate `SKILL.md` and run `status` without creating personal records.

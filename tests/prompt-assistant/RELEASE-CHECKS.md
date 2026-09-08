# v0.1.0 release checks

Executed on 2026-09-08, macOS arm64.

| Check | Result |
| --- | --- |
| CLI integration suite, Python 3.9.6 | 27 tests passed |
| Bundled Python 3.12.14 | Fresh status/init/context smoke checks passed |
| Codex Skill Creator `quick_validate.py` | Passed |
| UI metadata | Valid; default prompt names `$prompt-assistant`; automatic discovery enabled |
| Local Markdown resource links | 24 links resolved |
| Standalone JSON documentation examples | 3 parsed successfully |
| Behavioral evaluation specification | 15 unique synthetic cases; not executed as a model benchmark |
| Release archive | 14 public files; source bytes verified after extraction; no runtime database or Python caches |
| Extracted archive | `status` ran successfully without creating personal data |

Release archive SHA-256:

```text
939dab87c2e57124fda1c450af7b27ef9e688861a22821265a99de4c8dd1883a
```

These checks establish packaging and memory-tool behavior. They do not establish improved downstream image/video/text quality or reliable execution by every host model. The next evaluation layer is the host-agent protocol in [EVALUATION.md](EVALUATION.md), using actual user feedback and tool outputs.

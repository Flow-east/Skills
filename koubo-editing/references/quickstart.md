# 快速使用

## 一键预览

```bash
python3 scripts/run_auto_pipeline.py /absolute/video.mp4 --out-dir /absolute/output
```

可选：`--title`、`--template auto|list-cards|knowledge|service`、`--shot-type wide|medium|close`、`--model /absolute/model`、`--backend mlx|faster|whisper`。

一键模式会生成本地转写、自动计划、模板预览、复核报告和 QA。默认不自动删除现场沟通/重录，也不会自动调用生图服务；如需快速清理句中、带明显停顿的高置信填充词，可显式加 `--remove-high-confidence-fillers`，仍需检查报告。

## 复核后最终剪辑

先阅读 `auto_plan_review.md`，建立只包含用户确认编号的文件：

```json
{"accept":[2,5]}
```

再运行：

```bash
python3 scripts/apply_review.py auto_plan.json --review review.json --out final_plan.json
python3 scripts/render_template.py final_plan.json --out-dir final_render
```

## 精细字幕与画面事件

复杂的“场景/答案两层”“预留槽位插入”“中英独立轨道”“圆形人物/模糊带”写入 `caption_events`、`runs`、`english`、`viewport_events`；详细字段见 `references/plan-format.md`。贴纸必须是实际透明素材，缺素材时再使用当前环境可用且获授权的生图工具生成。


## 模板变体

一键预览可指定已验证变体，例如：

```bash
python3 scripts/run_auto_pipeline.py VIDEO --out-dir OUT --template-variant tpl-orange-line
```

当前目录由 `assets/template_catalog.json` 管理。可用 `scripts/template_library.py eligible` 查看模板 ID，并通过 `--template-variant` 选择。

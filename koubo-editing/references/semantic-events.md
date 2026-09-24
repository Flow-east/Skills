# 语义事件生成

`make_cut_plan.py` 的 `auto_semantics` 是保守候选生成器，不是语言理解替代品。开启后，它只从已对齐的词级转写中寻找明确的结构词：否定/避坑、警示、序号/数字、推荐、结论、转折。生成的 `semantic_marks` 必须在交付前结合原音和上下文复核；它不会生成未说出口的标题、结论或产品背书。

复杂情况由编辑者显式提供 `semantic_marks`：

- `negative` / `warning`：可使用红橙强调和射线，必要时再绑定 X 或指示符号；
- `recommendation`：黄色关键词和轻爆发；
- `number`：青绿色数字/序号和闪点；
- `conclusion`：青绿色结论词和短爆发；
- `transition`：较轻的粉色/闪点过渡。

自动候选宁可漏标，也不要把每个名词都包装成重点。品牌名、专名、数字和事实性推荐仍需保留校对项。

如果计划明确开启 `auto_viewport:true`，`conclusion` 节点会获得很短的轻暗角，`number` 节点会获得短暂圆形人物画布候选；这是克制的候选效果，不会对每个字幕强行切场。双人/访谈素材如需“中间清晰带+上下模糊背景”，可在片段上显式写 `viewport_events.kind:"blur_band"`，并设置 `band_height`。

## 自动预览计划

`scripts/auto_plan.py` 可从带逐词时间码的转写 JSON 生成一份 `reference_mode` 预览计划：按约 0.72 秒停顿分组、启用 `auto_semantics`/`auto_viewport`，但默认**不判断重录、现场沟通或事实正确性**；可选用 `--remove-high-confidence-fillers` 仅删除句中且有明显停顿的高置信填充词，普通“对/好的/好”不会因出现一次就删除。它适合快速得到视觉预览，不可替代 Codex 对转写上下文的编辑决策；交付前必须复核 `review` 中的未决项。

## 一键预览

`scripts/run_auto_pipeline.py VIDEO --out-dir OUT` 会依次执行本地转写、停顿分组计划和参考式渲染，输出 `transcript/raw.json`、`auto_plan.json`、`render/final.mp4` 与 `render/qa.json`。它是保守预览入口，不会自动删重录/现场沟通，也不会自动调用付费生图；正式交付仍需在计划层复核语义和贴纸。

自动预览计划还会把跨停顿重复的 4 字以上短语列为“可能重录/重复表达”候选；它只写入 `review_candidates`，不会自动删除任何一遍。只有结合语气、画面、纠正上下文确认后，才应在 `removed` 中做剪辑决定。

## 应用复核结果

`apply_review.py PLAN --review REVIEW.json --out FINAL_PLAN.json` 只接受用户明确列出的 `accept` 候选编号，例如 `{"accept":[2,5]}`；它会把候选写入 `removed`，并把保留片段按删除区间安全切开，避免相邻片段拼接时把已删语音带回。没有明确接受的候选不会被删除。

语义 mark 可选 `sticker` 和 `sticker_reason`。只有编辑者明确认为文字不足以表达语义时才填写，例如 `negative` 配 `cross`、`warning` 配 `pointer`；编译器只记录 `sticker_candidate`，不会因此自动消费 Nexora 额度，实际生成前仍需检查本地素材和授权。

语义类型还会提供保守的默认入场：推荐/结论使用轻弹入，警示/转折使用上移，数字使用缩放；编辑者可用 `enter` 覆盖。默认动效不代表固定照搬某一款官方模板，而是按样本归纳的可配置候选。

推荐 mark 会默认使用 `layout:"scenario_choice"`：前面的场景/连接词缩小，后面的答案词放大并作为第二层重点；可显式改成其它 layout。它仍是保守排版候选，复杂句式由编辑计划手工提供 runs。

# 隐私目标与遮挡改稿

## 先决定保护范围，再选择样式

扫描画面、口播、字幕和交付文本；用户明确指定的对象直接列入目标。AI 发现但不确定是否属于私密内容时，标记 `pending`，说明时间点并确认；未确认前不要称公开版本已脱敏。无目标时不加遮挡。用户只说“遮住姓名”无需追问贴纸样式：按对象、构图及模板选择可靠方案并做初版。用户指定样式时优先遵从；不支持则解释缺口并问可否改用等效覆盖，不暗换。

内置程序化遮挡方案（由 `scripts/privacy_masking.py` 定义，不需外部图片）：

| ID | 外观 | 适合 | 注意 |
|---|---|---|---|
| `cloud` | 浅色柔边云团，核心实心 | 小块文字/物体 | 柔边只能在核心外；用户提供具体参考时还要核对轮廓 |
| `paper-strip` | 浅色纸条 | 文字、屏幕局部 | 比云团利落，不适合未验证的大幅运动人脸 |
| `solid-card` | 深色圆角实心卡 | 文字、屏幕、面孔 | 较醒目，可配模板但核心始终不透明 |
| `face-patch` | 深色面部实心贴 | 面孔、局部物体 | 不能替代人物追踪；实测连续运动 |
| `face-oval` | 浅色实心椭圆 | 面孔 | 与深色方案区分，但仍须实测覆盖与主体关系 |

这些方案与关键词装饰贴纸独立。仅程序化图形，随技能源码按仓库 MIT 许可；没有付费或外发素材。`privacy_mood: "editorial"` 或 `"warm"` 可建议纸条，否则文字默认云团、屏幕默认信息卡、面孔默认实心贴。AI 仍要依据实际画面检验安全区与主体，不能只凭类型盲选。

## 剪辑计划

在 `clips` 和 `scene_*` 之外填写成片时钟的目标与事件。`visible` 是目标实际可见的每个**剪辑片段实例**，不是自动检测结果；`box` 是镜头缩放和 scene 画面操作**之后**的敏感核心坐标，格式为 `[x,y,width,height]`，均为 0–1 的成片相对尺寸。这里不是原片坐标，也不是安全边缘：渲染器会在核心外扩边并确保核心不透明。`start/end` 必须按输出帧对齐，覆盖每一个可见帧。隐藏于前景的时段可拆开 `visible` 区间；能力不足时不要假装已处理复杂前后遮挡。

```json
{
  "privacy_targets": [{"id":"name-1","kind":"text","origin":"user",
    "status":"confirmed","reason":"桌牌姓名","modalities":["video"],
    "visible":[{"clip_id":"intro","start":0.5,"end":1.5}]}],
  "privacy_events": [{"id":"cover-1","target_id":"name-1","clip_id":"intro",
    "start":0.5,"end":1.5,"motion":"static","box":[0.7,0.25,0.18,0.07],
    "style_id":"cloud"}]
}
```

可省略 `style_id` 让技能推荐。移动目标改用 `motion:"keyframes"` 和 `keyframes:[{"time":0.5,"box":[...]},...]`；首末关键帧必须覆盖事件边界，中间最多相隔约 0.25 秒，区间采用相邻核心框的保守包络。**这仍是经人工定位的关键帧，不是自动物体跟踪，也不能仅凭计划证明目标位置准确。**每个复用片段实例都应有自己的目标可见区间和遮挡事件。需要结尾停帧时可用 `tail_hold_frames`（0–5 秒内的整数帧数）延长最后画面和静音音轨，并把仍可见目标的 `visible` 与事件延长到新的 `plan.duration`；若外部后期另行延时，须重新映射遮挡并复核最终编码，不能沿用旧 QA。

如隐私目标涉及声音，增加 `modalities:["video","audio"]`，在目标内用 `audible:[{"clip_id":"intro","source_start":0.6,"source_end":0.9}]` 列出每个有声片段实例，再填写对应的 `audio_redactions:[{"target_id":"name-1","clip_id":"intro","source_start":0.6,"source_end":0.9}]`；该段原声会静音，别把画面覆盖当成消声。需隐藏字幕/附带文本时再加 `"text"`、`"text_review":"redacted"` 和当前目标私密的 `match_terms`。渲染器会在编译副本中把匹配文本替换为 `[已隐藏]`，并扫描导出的中英字幕、译文和标题。**原始编辑计划和源视频仍含敏感信息，必须保存在非公开工作区；不要把原计划和原片一起发送给成片接收人。**未命中跨词/画中文字或未出现于词表的泄露仍需要人工复核。

## 成片复核与反馈

`privacy_qa.json` 提供遮挡事件、风险帧、文字扫描及三项独立结论：`coverage`（覆盖）、`composition`（构图）、`style`（外观）。机器预检通过后仍为 `pending_encoded_visual_review`；`public_delivery_allowed:false` 表示**不可仅靠机器报告宣称脱敏版可公开交付**。原尺寸连续查看敏感对象出现到消失、切点前后、缩放极值、运动/前景遮挡及最后几帧，并试听声音与核对所有字幕/缩略图；先修漏码，再谈好看。可用 `python3 scripts/privacy_review.py /absolute/render --out-dir /absolute/private-review` 导出原尺寸、带声音的连续区间供人工复核；这些短片仍不是审核通过的公开成品。

用户觉得遮挡突兀时，针对目标局部生成两三款同段对比预览：

```bash
python3 scripts/privacy_revision.py preview plan.json --target-id name-1 --out-dir /absolute/private-preview
```

该脚本会从原计划分别完整渲染再截取同一短段，预览只供选择，不能当脱敏最终片。用户选定后，仅改对应目标的遮挡样式并保存新计划，再用常规渲染器完整重渲染、检查所有受影响画面与音轨：

```bash
python3 scripts/privacy_revision.py apply plan.json --target-id name-1 --style paper-strip --out-plan /absolute/updated-plan.json --user-selected
python3 scripts/render_template.py /absolute/updated-plan.json --out-dir /absolute/updated-render
```

`--user-selected` 只能在用户明确选定后使用。指出“跟丢/漏字”不是外观反馈：先修目标定位与轨迹；改变“遮不遮某人”等范围要重新确认音频、字幕和画面。用户明确要求另一种柔边团状参考时读 [柔边外观规则](privacy-soft-mask.md)。

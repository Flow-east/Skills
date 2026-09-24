# 隐私目标与遮挡改稿

## 先决定保护范围，再选择样式

扫描画面、口播、字幕和交付文本；用户明确指定的对象直接列入目标。AI 发现但不确定是否属于私密内容时，标记 `pending`，说明时间点并确认；未确认前不要称公开版本已脱敏。无目标时不加遮挡。用户只说“遮住姓名”无需追问贴纸样式：按对象、构图及模板选择可靠方案并做初版。用户指定样式时优先遵从；不支持则解释缺口并问可否改用等效覆盖，不暗换。

内置遮挡方案（`scripts/privacy_masking.py`；完整目录见 [贴纸库](sticker-library.md)）：

| ID | 外观 | 适合 | 注意 |
|---|---|---|---|
| `mosaic-neutral` | 中性方块马赛克 | 姓名牌、号码、屏幕信息 | 云朵构图不合适时使用；不采样原始敏感像素 |
| `mosaic-warm` | 暖色方块马赛克 | 姓名牌、号码、屏幕信息 | 暖色模板中使用 |
| `mosaic-charcoal` | 深灰方块马赛克 | 姓名牌、号码、屏幕信息 | 严肃/科技风，也适合浅色名牌 |
| `cloud` | 动态柔边云朵 | 姓名牌、短文本、局部物体 | 默认局部文字方案；按目标范围重算轮廓，柔边只在不透明核心外 |
| `brush-swipe` | 不规则笔刷 | 文字、屏幕局部、物体 | 视觉轮廓不规则；核心完全实心 |
| `pixel-confetti` | 像素碎片 | 文字、屏幕、面孔、物体 | 不透明像素图案，不读取原画面像素 |
| `mascot-cloud` | 云团表情 | 人脸、物体 | 轻松题材；移动目标需逐帧复核 |
| `flower-doodle` | 涂鸦花朵 | 人脸、物体 | 轻松或编辑风；不要当通用屏幕遮挡 |
| `sleepy-cloud-cover` | 瞌睡云团 PNG | 人脸、物体 | 温柔口吻；验证整张脸和构图 |
| `orange-flower-cover` | 橘色花朵 PNG | 人脸、物体 | 明快口吻；留意较宽轮廓 |
| `mint-cat-cover` | 薄荷猫咪 PNG | 人脸、物体 | 轻松口吻；不宜严肃场景 |
| `pixel-creature-cover` | 像素小怪兽 PNG | 人脸、物体 | 游戏/科技风；边缘较宽 |

遮挡只是 [贴纸库](sticker-library.md) 的一个子类。关键词强调贴纸不能用来替代遮挡。用户未指定样式时按对象、语境和构图自动选择，试看成片后再调整；姓名牌优先按文字范围生成柔边云朵，构图不合适时再用方块马赛克，不默认添加规则卡片。另有 12 款生图透明 PNG 可用于普通装饰；只有上表 4 款生图贴纸具备覆盖验证。库中不包含剪映素材。

## 剪辑计划

在 `clips` 和 `scene_*` 之外填写成片时钟的目标与事件。`visible` 是目标实际可见的每个**剪辑片段实例**，不是自动检测结果；`box` 是镜头缩放和 scene 画面操作**之后**的敏感核心坐标，格式为 `[x,y,width,height]`，均为 0–1 的成片相对尺寸。这里不是原片坐标，也不是安全边缘：渲染器要求核心完全不透明；生图贴纸无法放入画幅或盖住旁边必要信息时换款。`start/end` 必须按输出帧对齐，覆盖每一个可见帧。隐藏于前景的时段可拆开 `visible` 区间；能力不足时不要假装已处理复杂前后遮挡。

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
python3 scripts/privacy_revision.py apply plan.json --target-id name-1 --style brush-swipe --out-plan /absolute/updated-plan.json --user-selected
python3 scripts/render_template.py /absolute/updated-plan.json --out-dir /absolute/updated-render
```

`--user-selected` 只能在用户明确选定后使用。指出“跟丢/漏字”不是外观反馈：先修目标定位与轨迹；改变“遮不遮某人”等范围要重新确认音频、字幕和画面。用户明确要求另一种柔边团状参考时读 [柔边外观规则](privacy-soft-mask.md)。

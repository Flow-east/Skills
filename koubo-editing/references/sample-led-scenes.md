# 样片驱动的三套分层模板（第一批校准）

当前状态：**已实现、已做技术/画面校准，等待用户审美验收**。不是开拍官方字体或工程；不能把54套已分析样片称为54套已实现模板。旧的 `ink_note / cream_serif` 仍兼容既有计划，新任务优先选下面对应的分层版本，不自动重渲染历史交付。

新模板库状态和正式/预览选择见 [模板库](template-library.md)，新增五套见 [第二批](batch2-scenes.md)。本页只定义首批三套，不代表技能只有三套。

## 选中模板即绑定整套规则

| template_variant | 字体角色 | 字幕规则 | 独立词标 | 视频层效果 |
|---|---|---|---|---|
| tpl-soft-pink | Noto Serif SC：正文650、重点750、标题800 | 一组1–2个短语，前句左上、后句右下；各有自己的出现/退出；白正文+粉重点，显式warning用黄 | 无底衬线词标，仅在安全的模板槽位使用；不是每组必加 | 暗角、真实像素圆窗、近似横移拖影 |
| tpl-white-gold | Noto Sans SC：标题900、正文800 | 每组一个紧凑短句；棕字心+奶白轮廓，不铺大底板；单行金色标题持续 | 同族轮廓词标，可显式加原创红叉 | 近似横移拖影；标题不跟着变模糊 |
| tpl-blue-purple-grid | Noto Sans SC 900标题/正文；Smiley Sans词标 | 标题逐字有有限大小变化，紫青偏移轮廓；正文在点阵白底窗口横条内；每组一个短句 | 紫绿偏移轮廓+小色条，独立时钟 | 此版未实现额外视窗/镜头转场；不冒用其他模板效果 |

蓝紫方格的原方块切角字库未识别；当前粗黑替代字形仍有差距。ZCOOL QingKe HuangYou曾作候选，对照后过细长，未作为该模板最终标题使用。字库文件及来源/授权见 `assets/fonts/manifest.json`。变量字体轴必须在绘制与字形QA中一致，否则Noto默认细字重会与设计不符。

## 编写计划

仍用 version=2 的剪辑计划：clips内 words 使用原片source秒，先按原流程做内容取舍。新 `scene_*` 字段**全部使用剪切后output秒**，要求 `scene_time_space: "output"`；不把原片秒直接填进这些字段。以帧量化后的剪切结果计算时钟，剪切变更后必须重建场景计划。

- `scene_title_lines`：作者按语义分好的1–2行（金色版只接收单行简短标题），不让字符计数任意拆标题；`title_duration` 可覆盖模板默认时长。
- `scene_captions`：依次排列、不重叠的字幕组；每组有start/end及phrases。每个phrase有自己的start/end以及text或runs；phrase必须在组内、按进入顺序排列。pink最多2个phrase；gold/grid只接收1个，不能强行共用pink版式。
- `runs`：`text`与`role: body|keyword`。组内时间属于phrase，不属于run；需要更细时序就编成独立phrase，不假装已支持逐字时间。
- `tone: warning` 是显式选择，不用“包含不/别”这样的全局正则触发。
- 两短语组中的上句可保留至组结束；文字几何提前排好，第二句出现时不能让第一句跳位或重做入场。
- `scene_tags`：start/end/text/reason，可选side:left|right。只有金色模板支持symbol:cross（也可在主字幕phrase上显式设置，红叉会跟随短句，而非固定角落）。不是每个关键词都需要词标；说明真正的强调理由。发生遮脸/与字幕碰撞时调整文案、时间或模板布局，不能绕过预检强行叠放。
- `scene_canvas`：start/end/kind。仅能选该模板 `allowed_canvas` 内效果。circle的radius是**画面宽度的比例、换算成同一个像素半径**，center是宽高归一化中心；reason必填，说明构图理由并检查整段人物是否出圈。vignette可设strength 0–0.85。swipe最多0.8秒，是当前帧横向位移+多采样拖影的近似，不是恢复出的开拍原转场。
- `protected_regions`：当前成片上的手工检查区域，不是自动人脸跟踪。按最极端姿态与镜头缩放覆盖整个事件；文字动画包围框和各文字层相互碰撞都预检。
- 新模板不混用旧caption_events/viewport_events/keyword_stickers/card/clip.stickers，也不启用旧auto_semantics/auto_viewport。需要的是Codex主动编写scene事件，而非让用户手动补配置。

例：输入已编译成4秒输出，原话为“先检查工作，再评价员工”。

```json
{
  "template_variant": "tpl-soft-pink",
  "scene_time_space": "output",
  "title": "先检查工作",
  "scene_title_lines": ["先检查工作"],
  "scene_captions": [
    {"start": 0.2, "end": 3.8, "phrases": [
      {"start": 0.2, "end": 3.8, "runs": [
        {"text": "先检查", "role": "body"},
        {"text": "工作", "role": "keyword"}
      ]},
      {"start": 1.8, "end": 3.8, "text": "再评价员工"}
    ]}
  ],
  "scene_tags": [],
  "scene_canvas": []
}
```

这是插入完整计划的片段，不是可独立运行的剪辑计划。不要复用示例文案/时间到用户视频。

## 运行与检查

仍调用 `scripts/render_template.py`。它按scene_system路由到新引擎，预检字体、完整动画范围、手工保护区和图层相撞。主口播文字在忽略标点/空白后必须与保留words一致，缺词/替换会报错；强调、词标不能改写主字幕。SRT按实际可见短语和保留状态输出，而非继续套旧13字分组。

合成顺序：已剪视频→全局camera_motion（若编排）→视频层暗角/圆窗/转场→标题→独立短语→词标。字幕不随视频层变暗、被圆窗裁掉或随视频转场变糊。旧viewport分支也已调整为先处理视频，再叠标题。

先看同词原样对照，再看至少一条替换文案的动态预览。尤其检查：第二句进入时前句不跳位、圆窗未变椭圆、长句不溢出、词标不遮脸、转场期间标题清晰、最后音节后留余量。字体QA/单元测试通过只代表技术检查；不能宣布已达到开拍审美或“1:1还原”。

原校准实样和研究视频属于用户本地资料，不随公开技能分发，也不是技能运行依赖。

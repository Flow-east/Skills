# 第四批中四套：独立契约校准版

继续遵守creative-direction：先定内容结构、开场、表现形式、音效、转场、隐私，再选择整套模板。这里是校准实现，非原版引擎/工程或审美验收。新素材需重新预检，不直接复制演示坐标。

|ID / 入口|整体风格|正文/贴纸能力|已知核心差距|
|---|---|---|---|
|kp-19 荧光绿 / `ref_neon_v1`|白色斜方括号标题，荧光宋体副标题与下划线；轻白正文与粗荧光重点|最多三句独立时钟错位留屏；可选圆窗需构图理由|非逐字插入曲线；不能仅为装饰/规避隐私裁掉人物手势|
|kp-20 Ultra·紫 / `ref_purple_v1`|紫粗斜标题、白小副题；轻正文/粗重点反差|normal横排、bilingual独立英文、vertical直立逐字竖列；紫色侧标|几何倾斜为替代字形；未做人物身份竖牌|
|kp-26 暖系橙黄 / `ref_warm_v1`|站酷快乐圆趣标题、橙/奶油/深红边；白正文黄重点|最多三句，各有紧贴橙底与错位位置、整块pop入场|未做原点赞/定位贴纸、黑幕揭示、发光尾标；参考640×852适配3:4/9:16|
|kp-29 基础黑白 / `ref_mono_v1`|白斜标题配逐行黑底，白厚边正文加橙重点|单句稳态、独立橙色直立竖词标|跟随头部聚光及双镜头模糊转场未做；严禁用圆窗伪装聚光|

## 编排 schema

复用 `scene_time_space: output`、`scene_title_lines`、`scene_captions`。每个phrase有唯一`id`及独立start/end；正文仍须等于保留的逐词转写。短语只改变换行/留屏，不增删原话。`runs`只准body/keyword，不支持自定义fill、pointer、旧notes/identity/callouts/highlights。不支持的能力必须报错，不静默丢层。

Neon/Warm每组最多3句，Purple最多2句，Mono最多1句。保留前句时显式延长其end，不重设start；总长度超安全区就重组短句，不无限缩字。Warm每句独立底条，不把整个组包进卡片。

Purple `mode: bilingual`须在`scene_translations`中有一条对应phrase_id、source_text完全一致的英文，`language: en`、独立输出start/end（在该中文句内）、review_status和reviewer。普通/竖排态不得偷偷携带不显示的译文；英文另存SRT。未核验译文只能明确preview。

Purple `mode: vertical`逐字直立排版，非整句旋转。每句最多10字；显式归一化左上角`x/y`及`reason`。同组都为vertical；整条竖列必须经过画幅/人物保护区/标题/侧标碰撞检查，不能自动在脸上排字。中文长列可用独立合成演示测试，不强行塞进真实样片。

`scene_tags`需`phrase_id`、`text`（当前原话内短词）、独立start/end（限该句区间）、`reason`，左右槽。Purple/Mono可`orientation: vertical`（最多4字），其他仅horizontal。不伪造身份或地点，不捆绑无关图标。Neon圆窗沿用显式center/radius/reason和构图审核要求；Mono没有spotlight能力，传入必须失败。

## 验证口径

固定0914中文/剪口的3:4与9:16样片；Mono另做完整集成；合成测试覆盖三层持留、直立列及Neon圆窗。检查字形、边界、保护区、所有解码帧、AV时长、原话/剪口和尾部时码余量。正常速度视听和用户审美另计，不以静帧检查冒充。

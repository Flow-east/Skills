# 计划 v2

编译前先完成 [通用创作决策](creative-direction.md) 中的 `creative-brief.md`，再依据选中模板将意图映射到本规范支持的字段。创作方案是决策文档，不是渲染接口；已实现的语义音效用 [sound-design.md](sound-design.md) 的显式事件；不能把尚未实现的转场或跟踪要求作为未知字段写入后宣称完成。源片段前置/重复时区分片段实例，并重新核对所有输出事件时间。

**画幅先决策（渲染硬门槛）。**渲染前读取源的显示宽高比（含 SAR/旋转）。顶层 `frame_fit` 可选 `native`（目标与源同显示比例，不补边、不裁切）、`cover`（铺满目标画幅，会裁两侧/上下）、`contain`（保留全部源画幅，会补边）。源/目标比例不同且**未显式选择**时直接拒绝渲染；选择 `cover` 或 `contain` 时还须写出非空的 `frame_fit_reason`，说明用户要求/参考依据与主体、手势、隐私的取舍。`native` 比例不符也会拒绝。比例相同的旧计划可继续渲染，不能因此声称已人工验收。`auto_plan.py` 默认按原片比例生成 `native` 计划；显式传入不同尺寸会失败，不暗中加边或裁切。`qa.json.frame_fit_audit` 记录源/目标显示尺寸、方式和理由。模板只支持另一比例时，先核对兼容能力并说明冲突，不能靠补黑边悄悄迁就。

原始词级时间码均为**源视频秒数**；渲染器编译为整数帧后，所有音画、字幕、贴纸、音效使用同一个源/成片映射。原始视频即使 VFR、名义60实际30，也不直接拿名义帧率当时间计数。

最小示例（占位路径需换成真实绝对路径）：

```json
{
  "version":2,
  "source":"/absolute/source.mp4",
  "source_duration":20,
  "font":"/absolute/chinese-font.ttc",
  "width":720,"height":1280,"fps":30,
  "template":"knowledge",
  "title":"先把需求讲清楚",
  "eyebrow":"表达方法",
  "title_duration":2,
  "audio":{"bed":"none","cues":true},
  "clips":[
    {
      "id":"point1","start":3.0,"end":5.0,
      "reason":"保留明确观点，排除上一段试录",
      "words":[{"text":"先讲需求","start":3,"end":4}, {"text":"再讲方法","start":4,"end":5}],
      "card":{"label":"表达顺序","value":"先讲需求","at":3.0},
      "zoom":1.0,"focus":[0.5,0.5]
    }
  ],
  "removed":[{"start":0,"end":3,"reason":"试录"}],
  "review":{"status":"preview","unresolved_terms":[]}
}
```

可省略 title 和 card（不能虚构语义），但每段要有 words 或明确 caption。`make_cut_plan.py` 接收同样格式的 decisions，未提供 words 时从原始转录筛选；修正字幕时保留独立原始 JSON，不覆盖识别证据。`allow_reorder:true` 才允许倒序；需要实际剪辑理由，不能默默改原意。

贴纸附在 clip 的 `stickers`：`path`（真实绝对路径），`start/end`（源时间，必须落在当前clip内），`x/y/width`（相对画幅0–1），`reason`。贴纸宽按实际主体裁除透明边后计算。注意其高宽比，超下边界会报错，不自动裁掉主体。

`audio.normalize` 默认 true，根据各保留片段实测 RMS 做有上限的人声音量平衡，避免采访提问特别响、回答很小；音量测量和增益保存在编译计划，不做过度降噪。

`audio.bed` 可为 `none` 或 `original-pulse`（本地合成极轻节拍），`bpm` 默认100。`cues` 决定是否在每张卡片 at 节点生成轻提示音。使用 `sound_events` 时必须 `cues:false`，按唯一片段实例映射和素材击点对齐，详见 [音效设计](sound-design.md)。没有真实CTA时不要增加手势贴纸。

验证会拒绝：非法/空片段、非有限时间、缺失路径、没有字幕内容、乱序未声明、词时间越界、与 removed 相交的保留片段。切点按 fps 四舍五入，音画一致；原视频字幕已经烧录时不可直接二次叠字，应先判断是否能合理避让或保留。


## 开头钩子与镜头边界（可选）

`auto_plan.py` 默认保持原顺序，在 `plan.json` 旁生成 `_hook_candidates.json` 与 `.md`；也可运行 `python3 scripts/opening_hooks.py plan.json --out /absolute/候选.json`。候选只是源片段/原话/风险，不自动承诺改序。经原声和上下文复核后才可在计划顶层填写 `hook_design`：

```json
{
  "allow_reorder": true,
  "hook_design": {
    "method": "question_first",
    "opening_clip_ids": ["question"],
    "source_excerpt": "为什么先做这一步？",
    "reason": "真实提问在开头完整成立",
    "semantic_review": "verified",
    "end_of_speech_review": "verified",
    "payoff_clip_id": "answer",
    "payoff_reason": "正文实际说明该步骤的原因",
    "duplicate_policy": "moved_not_repeated"
  }
}
```

`opening_clip_ids` 必须是输出片段顺序的前缀，`source_excerpt` 必须出自其逐词原话；`original` 不要求重排。其他可用方法为 `result_first`、`highlights`。前置时必须 `allow_reorder:true`、指定位于开场后的回应片段和不重复策略；有意再现需 `intentional_reprise` + `reprise_reason`，依赖前文的指代/转折需 `dependency_resolution`。词末源时间不能越过片段剪口；机检不等于验证声波尾音、事实条件、画面动作或钩子兑现，须人工核对。不要把举例字段原样套进新视频。

顶层 `boundary_transitions` 指定输出顺序中**相邻的两个片段实例**；省略即普通直切。每个剪口最多一个事件：

```json
{
  "boundary_transitions": [
    {"after_clip_id":"opening", "before_clip_id":"body", "kind":"dip_to_dark", "frames":8,
     "reason":"预告进入正文", "speech_clearance_verified":true, "color":"#101018"}
  ]
}
```

`kind` 只支持 `cut`、`match_cut`、`dip_to_dark`；前二者不改变画面时间，仅记录编辑意图，`match_cut` 须附 `match_basis` 并看成片证明构图/动作相接。`dip_to_dark` 支持 4–18 帧且不超过 0.65 秒，须两侧静音、足够画面余量，编译器检查已有逐词时间码不压词；手动填 `speech_clearance_verified:true` 前仍须听原声并检查呼吸、尾音和未转写语音。压暗发生在字幕、贴纸及隐私遮挡合成之后，不改变源音频与输出时长，也不是交叠叠化/方向擦除。检查 `transition_qa.json` 与切点帧，试听 A/B；未复核不要写“已通过”。

## 模板化字幕事件（可选）

为了接近真实模板，优先使用事件层而不是大卡片。顶层可加入 `reference_mode:true`、`caption_events` 和 `viewport_events`：

```json
{
  "reference_mode": true,
  "caption_events": [
    {"text":"我做    的", "start":0.8, "end":1.4, "position":"lower_center", "style":"base"},
    {"start":1.02, "end":1.9, "position":"lower_center", "runs":[
      {"text":"我做", "style":"base", "size":42},
      {"text":"自媒体", "style":"keyword", "size":57, "fill":"#B8342E", "extrude":true},
      {"text":"的", "style":"base", "size":42}
    ]},
    {"start":2.0, "end":2.5, "position":"lower_right", "runs":[{"text":"三字真言","style":"base","size":30,"fill":"#D8C7C0"}]}
  ],
  "viewport_events": [
    {"kind":"circle", "start":4.0, "end":6.0, "center":[0.5,0.42], "radius":0.34, "background":"#F8F0DF"},
    {"kind":"dim", "start":6.0, "end":7.0, "alpha":0.28}
  ]
}
```

事件时间使用**成片时间**；`position` 可用 `top_left`、`top_center`、`middle_left`、`middle_center`、`lower_left`、`lower_center`、`lower_right`，也可直接传 `[x,y]` 相对坐标。`runs` 用于句内不同字号、颜色、描边和挤压效果；英文应作为独立 run 或独立事件，只有存在可靠翻译时才添加。`viewport_events` 是画布状态，不应拿来遮挡人物脸部。旧版 `card` 和 `words` 仍受支持，但不要在同一语义节点同时堆大卡片和长字幕。

当 `reference_mode:true` 且片段没有显式 `caption_events` 时，渲染器会把词级时间码按停顿/长度组成短语事件；只有词对象带 `"emphasis":true`，或片段带 `emphasis_words`，才会自动放大并换主题色。它不会擅自判断“哪个词重要”，避免把普通字幕误包装成错误观点。需要复杂的插入、错位或渐进填充时，必须由编辑计划显式写 `runs`。

字幕事件可选 `effect:"sparkle"`、`"burst"` 或 `"rays"`，用于标题/关键词周围的少量程序化闪点或射线；它们必须绑定具体语义事件，不要全片常驻。可用 `effect_color` 和 `effect_radius` 微调。涉及真实物体、人物或品牌图形时，仍应使用透明素材并经过语义判断，而不是用程序图形冒充贴纸。

`make_cut_plan.py` 还支持由编辑者提供 `semantic_marks` 自动生成基础 rich-text 事件。每个 mark 可写 `start/end`、`label`、`value`、`accent`、`position`、`keyword_size`、`base_size`、`extrude`、`effect`；它只会在对应片段有重叠词时生成事件。该机制是“语义决策的编译器”，不是用正则替代理解。

`semantic_marks.kind` 可使用 `recommendation`、`negative`、`warning`、`number`、`conclusion`、`transition`。未显式指定强调色/效果时，会采用保守默认：推荐偏黄并轻爆发，否定/警示偏红橙并用射线，数字/结论偏青并用闪点或爆发，转折偏粉并用闪点。默认只是视觉候选，编辑者仍可覆盖，且不自动生成事实性文案。

字幕事件可选 `english:{"text":"...","start":...,"end":...,"size":22}` 作为独立英文轨道；它可以比中文晚入场、提前退场或只显示关键词。没有可靠翻译时不要填入 `english`。

双语计划可选 `bilingual_style:"premium"`；`service` 模板默认采用更小、更低不透明度的英文副层，`knowledge`/`list-cards` 保持更清晰的英文辅助层。该样式只影响已确认的 `english` 字段，不会生成翻译。

计划可选 `style_profile`：`contrast`（强对比黄）、`mint`（薄荷青科技）、`premium`（克制高级）、`warning`（红色警示）。profile 只提供默认颜色、字号和入场，事件显式字段优先；不要把样本文件名直接当作 profile，也不要声称还原开拍内部字体。

逐词字幕可加 `caption_break_after: true` 标出已复核的语义断句，SRT 与自动字幕使用相同分组；断句应落在词组之间，不拆“效率”“汇总数据”等词。仍受 `caption_chars` 字数上限约束，长句应预先分成短意群。


## 样片分层模板

当 template_variant 为 tpl-soft-pink / tpl-white-gold / tpl-blue-purple-grid 时，改用 [sample-led-scenes.md](sample-led-scenes.md) 的 scene_captions / scene_tags / scene_canvas，显式 scene_time_space=output；仍保留 clips.words 原片时间。新旧事件不能混用，SRT按真实短语可见状态输出。

## 第三批双语分层模板

`tpl-bilingual-wine-red` / `tpl-bilingual-ivory-luxe` / `tpl-bilingual-classic-blue` 按 [batch3-bilingual-scenes.md](batch3-bilingual-scenes.md) 编写唯一中文phrase ID及顶层 `scene_translations`，英文独立计时与导出，不使用旧phrase.english/english_map。译文校对状态明确，缺译/原文变更/时钟越界会阻断；这是渲染支持，不是自动翻译质量验证。

### 第三批后七套

见`batch3-seven-scenes.md`。navy最多3个错位短语；biyellow/brightyellow需要独立scene_translations。luxury/navy/news允许phrase.mode=display，vividblue允许label；其它状态显式拒绝。新七套scene_tags只能摘自一条当前短语且时钟完整位于其内，不能虚构参考里的身份或数字。

### B4a场景扩展

见batch4-scenes.md。shine/science的phrase.pointer摘唯一短词；green compact/display决定是否需要独立译文，scene_callouts可跨字幕保留概念；tech/science的scene_identity须可靠来源、复核和明确位置。其它模板拒收callouts/identity，防止默默丢层。

## B4b中四套扩展

见 [第四批中四套](batch4b-scenes.md)：`tpl-neon-green`、`tpl-ultra-purple`、`tpl-warm-orange`、`tpl-black-white`。逐套契约校准实现不等于审美验收；Purple翻译只用于显式bilingual，vertical需独立安全锚点。Neon/Warm最多三短语，Mono无聚光能力，不静默替代。

## B4c后四套扩展

见 [第四批后四套](batch4c-scenes.md)：`tpl-elegant-pink`、`tpl-promo-burst`、`tpl-professional-brown-gold`、`tpl-hot-pink`。秀丽粉双语单句或四条玫红短句；爆款促销默认无强制标题；金棕身份须真实核验；亮粉弧形字和漫画装饰仍受保护区约束。音效专项已恢复为显式事件原型，旧计划仍不自动加音效，未实现的抠像/人物描边不静默替代。


## B5a：暖线映橙、明快彩彩、古雅水绿、撕纸红

独立模式、语义下划线、保留侧标签及有来源/隐私核验的说明图卡见 [第五批前四套](batch5a-scenes.md)。校准版需显式预览；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。


## B5b：古典深棕、素雅姜红、黑黄框框、绿意漾漾

独立字幕状态、两槽功能签、繁中字形范围及显式复核的柔边圆窗见 [第五批中四套](batch5b-scenes.md)。校准预览不代表正式验收，音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B5c后四套校准版

tpl-minimal-ins / tpl-vintage-classic / tpl-translucent-yellow / tpl-minimal-torn-edge。独立状态、引用词签、可选圆窗及限制见[后四套规则](batch5c-scenes.md)。不得把校准实现计为正式全门槛验收；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B6a前四套校准版

tpl-minimal-yellow-white / tpl-crayon-cute / tpl-playful-pink-yellow / tpl-energy-cartoon。状态、原创语义符号、显式锚点与限制见[第六批前四套规则](batch6a-scenes.md)。不得把参考商品贴纸作为通用素材，也不得将校准版计为正式全门槛验收；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B6b中四套校准版

tpl-floral-travel / tpl-fashion-magenta / tpl-playful-detective / tpl-festive-red。状态、原创语义符号、参考事实隔离与限制见[第六批中四套规则](batch6b-scenes.md)。旅行/宿舍/价格/门店等参考事实不得跨视频复用；音效专项已恢复为显式事件原型，旧计划仍不自动加音效，校准版不计正式全门槛验收。

## B6c后四套校准版

tpl-red-comic-variety / tpl-soft-romance / tpl-monochrome-emoji / tpl-color-contrast-pop。状态、原创语义符号、参考事实隔离与限制见[第六批后四套规则](batch6c-scenes.md)。恋爱建议、MCN/SOP、人物滤镜和具体emoji资产不得跨视频复用；音效专项已恢复为显式事件原型，旧计划仍不自动加音效，校准版不计正式全门槛验收。

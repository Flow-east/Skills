# 第二批五套分层校准模板

这是可试用的独立设计实现，不是官方工程或已经用户验收的成品库。每套状态以 `template_progress.json` 为准；未验收使用 `template_delivery: preview`，正式交付不能默认选它们。共同时间规则、主词流一致性、分组、保护区和禁混旧图层要求仍见 `sample-led-scenes.md`。

| ID / 目标 | 整套绑定与编排 |
|---|---|
| `tpl-minimal-white` / tpl-minimal-white 简约白 | 粗主标题+细副标题左对齐；每组1–2个小短语，第一个紧黑半透底，第二个右下裸白；独立时钟；不加任意词标/画布效果 |
| `tpl-red-yellow-editorial` / tpl-red-yellow-editorial 高智红黄 | 金色衬线lead、白粗normal、红衬线display；每组最多2短语；黄色下划线侧注独立保持；可黑底inset |
| `tpl-taiwan-variety` / tpl-taiwan-variety 台式综艺 | 粗黑正文/重点字与粉绿黑白多边；normal倾斜、display放大、small恢复小字幕；最多2短语；缩放入场，不是每句都大 |
| `tpl-oriental-ink` / tpl-oriental-ink 淡雅新中式 | 马善政毛笔替代标题、霞鹜文楷正文；黑笔刷标题小红印记、细白normal或窄纸条paper；每组1短语，不加任意词标 |
| `tpl-butter-latte` / tpl-butter-latte 黄油拿铁 | 粗方字宽字距、暗偏移边；白/黄/薄荷/粉状态；最多2短语错位；奶油circle→inset→full由语义编排 |

标题对比度也要检查实际编码帧：黑色笔刷标题不能放到深色区域或补边黑条。`ink` 可显式设 `scene_title_surface: paper`，在标题原有范围加浅纸底，属于构图适配，不声称原样本总有底板。没有该字段保持裸字；其它模板不能套用该字段。

新增字段：
- 主字幕phrase的 `mode` 只允许对应模板表中的值，默认normal。latte允许normal/display，并允许 `color: normal|yellow|mint|pink`，不是任意配色。
- `scene_notes` 仅redyellow可用；每项 `{start,end,text,slot,reason}`，时间为output，slot为0/1/2。同槽不能重叠，不同槽独立保持。每条最多7字；与脸或其它文字碰撞会阻断。侧注是提炼摘要，不纳入主字幕词流，也不写入SRT。
- `scene_canvas` 新增 `inset`，只在契约允许时使用；`scale` 为0.7–0.94，reason必填。latte背景固定`#FCF9DD`，redyellow使用黑底。画面缩小不影响后叠文字。circle仍以宽度换算同一像素半径。
- 新5套只声明3:4、9:16。9:16测试仍需逐片人像检查，不能以一次测试推断任意人物安全。
- `camera_recipe` 是各套独立、有边界的原创参数，可通过 `camera_motion.build_track` 编译已审查的语义节点。比较包装可先固定镜头，但正常剪辑不能一律关闭镜头语言。模板内缩画框与相机推近是两个不同机制。

新增逐字显现、红黄同锚点接管、拿铁小光标及按语义触发的综艺心形装饰；动效必须按实际语义和安全区选择，不强制套用。字体使用许可替代字型，样片技术检查与具体视频审美确认分别记录。

文字由渲染器绘制；语义需要插画时，可按当前环境可用工具及授权条件生成。模板不以演示词或固定时间作为触发条件，Codex须根据实际视频编排字段。

# 54套目标与独立契约

`assets/template_targets.json` 定义54个风格目标；`assets/template_progress.json` 记录对应实现与验收状态。默认先运行：

```bash
python3 <SKILL_DIR>/scripts/template_library.py summary
python3 <SKILL_DIR>/scripts/template_library.py eligible
```

54 套已实现的模板默认可选、可用于剪辑，并在实际使用中持续优化；`in_use` 不等于用户已逐套审美验收。`eligible` 默认返回技术样片通过且没有关键阻塞的可用模板；`--preview` 仅用于检查尚未列为常规可用的校准项。一个目标保留多个历史版本也只算一套。

## 状态更新

设计、实现、技术、视觉、安装各自独立。`visual: in_use` 表示实际可用并持续优化，`limitations` 保留已知的参考差异，`blockers` 只记录阻断当前使用的问题。短样片通过是 `sample_passed`，不是全套QA通过。用户一般积极反馈保存在feedback，只有明确针对当前目标与版本的确认才记录 `accepted`。

`template_library.set_state()` 对技术通过、审美确认和安装验证要求证据文件存在、SHA256一致、目标ID/修订号一致。证据JSON至少含 `target_id, revision, passed`；用户确认还须有 `decision: accepted` 和真实 `user_quote`。证据引用含 `path, sha256, revision, reviewer, scope`。不能为通过门槛编造确认。

正式完成要求 implemented + passed + accepted + installed_verified 且无未解决阻塞。新修订须重做对应检查，不继承旧版验收。台账校验不会检查每个历史证据文件仍在本机；状态晋级操作才验证文件与哈希，发行时另做全量证据审计。

## 整套契约

`assets/template_contracts/tpl-<style>.json` 绑定角色字体/轴值、字幕位置与短语结构、词标、时序、镜头、支持比例和合成层级。`template_catalog.py` 加载契约后覆盖目录中的旧渲染字段，不允许目录与实际执行分叉。

- `template_contracts.validate(..., verify_assets=True)` 核对字体文件哈希和许可；`font_guard` 再按实际轴值检查显示文字。
- 不能向契约声明尚未实现的人物抠像/文字后置能力；缺核心能力应阻断，不套别的效果。
- 只接受已声明比例；模板迁移到新比例必须补布局/人像测试后再扩大支持列表。
- `template_delivery: accepted` 仅用于有正式验收证据的版本；当前可用版本使用 `preview`（这是交付门槛名称，不表示模板不可用）。旧计划不新增该字段仍可按历史行为渲染，但不代表正式验收。
- 渲染器负责执行，不会推断语义。Codex按参考设计、词流与画面主动编排场景，不向用户索要每个字幕坐标。

## 验收包目录约定

每套一个目标目录，保存：`design-card.md`、`type-comparison.jpg`、`primary/plan.json`、`primary/render/`、`alternate/plan.json`、`alternate/render/`、`review.json`、`release-evidence.json`。历史交付不搬移或覆盖，可用哈希引用。

设计卡需明确：参考哈希/实际时间点；观察与推断；字体角色及许可；识别性特征；布局、词标、动效和镜头规则；支持比例；已知差距；逐项技术与视觉检查结果。原样截图仅作研究对照，不能包成可分发模板素材。

每套必须有同词字体对照、同素材动态样片、不同文案/构图样片及边界检查。技术项目：主字幕一致、无缺字/越界/碰撞、完整解码、音视频时长误差≤一帧、尾音完整；视觉项目逐项检查字体、包装、布局、独立词标和动效。用户确认与机器检查分开；未实际试听写“未试听”。不能因未收到回复就自动通过。

## 第三批双语入口

当前前三套双语分层模板及明确variant ID见 [batch3-bilingual-scenes.md](batch3-bilingual-scenes.md)。按语义化 `tpl-` ID 选择，目录中其他基础变体不计入这54套参考目标。所有新视频仍先按 [creative-direction.md](creative-direction.md) 设计结构、声音、转场和隐私，再结合模板实现。

## 第三批后七套

百搭黄、顶奢、明快黄、沉稳墨蓝、新闻蓝、利落红、靓眼蓝的独立布局见`batch3-seven-scenes.md`。选用对应的语义化 `tpl-` ID；缺少的身份卡、镜像/追光/旋转框等能力记录在 `limitations`，不能对当前成片假称已实现。

## 第四批前四套

规则见batch4-scenes.md。新增shine/green/tech/science，这些模板可用于剪辑，视觉保持 `in_use`、正式验收单独记录；技术检查照常执行。不把动态样片数当成模板数，也不把合成身份卡测试当原片人物履历。

## B4b中四套扩展

见 [第四批中四套](batch4b-scenes.md)：`tpl-neon-green`、`tpl-ultra-purple`、`tpl-warm-orange`、`tpl-black-white`。逐套契约校准实现不等于审美验收；Purple翻译只用于显式bilingual，vertical需独立安全锚点。Neon/Warm最多三短语，Mono无聚光能力，不静默替代。

## B4c后四套扩展

见 [第四批后四套](batch4c-scenes.md)：`tpl-elegant-pink`、`tpl-promo-burst`、`tpl-professional-brown-gold`、`tpl-hot-pink`。秀丽粉双语单句或四条玫红短句；爆款促销默认无强制标题；金棕身份须真实核验；亮粉弧形字和漫画装饰仍受保护区约束。音效专项已恢复为显式事件原型，旧计划仍不自动加音效，未实现的抠像/人物描边不静默替代。


## B5a：暖线映橙、明快彩彩、古雅水绿、撕纸红

独立模式、语义下划线、保留侧标签及有来源/隐私核验的说明图卡见 [第五批前四套](batch5a-scenes.md)。渲染计划需显式设置 `template_delivery: preview`；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。


## B5b：古典深棕、素雅姜红、黑黄框框、绿意漾漾

独立字幕状态、两槽功能签、繁中字形范围及显式复核的柔边圆窗见 [第五批中四套](batch5b-scenes.md)。可用不等于正式审美验收，音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B5c后四套可用模板

tpl-minimal-ins / tpl-vintage-classic / tpl-translucent-yellow / tpl-minimal-torn-edge。独立状态、引用词签、可选圆窗及限制见[后四套规则](batch5c-scenes.md)。可用不等于正式全门槛验收；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B6a前四套可用模板

tpl-minimal-yellow-white / tpl-crayon-cute / tpl-playful-pink-yellow / tpl-energy-cartoon。状态、原创语义符号、显式锚点与限制见[第六批前四套规则](batch6a-scenes.md)。不得把参考商品贴纸作为通用素材，也可用不等于正式全门槛验收；音效专项已恢复为显式事件原型，旧计划仍不自动加音效。

## B6b中四套可用模板

tpl-floral-travel / tpl-fashion-magenta / tpl-playful-detective / tpl-festive-red。状态、原创语义符号、参考事实隔离与限制见[第六批中四套规则](batch6b-scenes.md)。旅行/宿舍/价格/门店等参考事实不得跨视频复用；音效专项已恢复为显式事件原型，旧计划仍不自动加音效，可用不等于正式全门槛验收。

## B6c后四套可用模板

tpl-red-comic-variety / tpl-soft-romance / tpl-monochrome-emoji / tpl-color-contrast-pop。状态、原创语义符号、参考事实隔离与限制见[第六批后四套规则](batch6c-scenes.md)。恋爱建议、MCN/SOP、人物滤镜和具体emoji资产不得跨视频复用；音效专项已恢复为显式事件原型，旧计划仍不自动加音效，可用不等于正式全门槛验收。

## ID 更新

模板目标和变体统一使用 `tpl-<style>`，音效使用 `sfx-<sound>`；旧编号不提供兼容映射。以前的剪辑计划若使用旧编号，应查看该计划选择的实际风格或声音，在当前目录中重新选择语义 ID 后再渲染。

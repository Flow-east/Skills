# 中文直播成交话术

[English](README.md) | **简体中文** · [← 返回全部 Skills](../README.zh-CN.md)

当前版本：[v0.1.0](https://github.com/Flow-east/Skills/blob/live-selling-script-v0.1.0/live-selling-script/README.zh-CN.md) · 发布日期：2026-09-01

`live-selling-script` 是一个用于共创、创作、审核和改写中文直播成交话术的 Agent Skill。它从产品事实、观众场景、可见证据、主播自然语言和真实行动路径出发，而不是把所有产品硬套进同一套销售模板。

## 适用场景

- 根据商品页、截图、产品说明、历史话术或其他已有资料创作直播话术。
- 将产品表达适配到视频号、抖音、淘宝直播、快手，或比赛与演示场景。
- 审核现有话术中的无依据主张、证据不足、书面感、通用 AI 腔和不匹配的行动指令。
- 将视频或音频中的忠实原话与后续结构分析、改写内容明确分开。
- 在产品事实已经完整时快速成稿，同时保留清楚的假设和待确认项。

Skill 可以输出产品事实卡、人群痛点地图、证据与异议地图、六步结构卡、可循环使用的 5–10 分钟单品话术、主播与场控提示、互动分支和聚焦具体问题的审核报告。

## 工作方式

默认采用渐进式共创流程：

```text
产品事实
→ 目标人群与痛点
→ 平台与主播声音
→ 证据、演示、异议与权益
→ 六步结构
→ 口语逐字稿
→ 事实、表达与转化验收
```

最终话术使用六步观众旅程：

```text
拉新进场
→ 痛点信任
→ 方法交付
→ 互动确认
→ 痛点延伸
→ 明确行动
```

它是一套判断结构，不是六段固定文案。每一步的权重、证据、节奏和行动路径都会随产品、平台、人群与购买决策变化。

四种工作模式让流程与需求保持匹配：

| 模式 | 适合情况 |
| --- | --- |
| 共创模式 | 从零开始、信息不完整，或产品定位需要仔细判断 |
| 快速成稿模式 | 产品事实完整，且用户明确要求直接出稿 |
| 审核模式 | 在改写前检查主张、证据、结构、口语表达和成交逻辑 |
| 转写整理模式 | 先保留可确认原话和听不清内容，再做分析或编辑 |

## 范围与边界

- 不会用行业惯例补全本产品的价格、库存、政策、效果和稀缺性。
- 无依据的信息会保留为假设或占位符；重要产品主张应对应可见或可核验的证据。
- 不虚构用户证言、订单、评论、倒计时或紧迫感。
- 不把产品能力改写成对用户最终结果的保证。
- 用户只要求审核、忠实转写或其他限定交付时，Skill 会停在对应边界。
- 平台规则会变化。内置基线和检查脚本不能替代当前官方规则核验、法律意见或专业合规审核。

## 安装

让 Codex 安装这个 Skill：

```text
请安装这个 skill：
https://github.com/Flow-east/Skills/tree/main/live-selling-script
```

也可以使用兼容的 Skills CLI：

```bash
npx skills add Flow-east/Skills --skill live-selling-script
```

从仓库副本手动安装到 Codex 时，请复制完整目录，以保留 `references/` 和 `scripts/` 的相对路径：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R live-selling-script "${CODEX_HOME:-$HOME/.codex}/skills/live-selling-script"
```

## 最短示例

```text
使用 $live-selling-script，和我共创一份课程直播成交话术。先读取我的现有资料，再告诉我成稿前必须确认什么。
```

如果使用的智能体支持自动发现 Skill，也可以直接用自然语言描述需求。

## 校验话术

内置检查脚本只依赖 Python 标准库。在仓库根目录运行：

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md
```

需要机器可读结果或严格模式时：

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md --json
python3 live-selling-script/scripts/lint_script.py path/to/script.md --strict
```

脚本会提示绝对化或结果保证、待核验的稀缺性与数字、价格锚点、命令式留人、未替换占位符和过长口语段落等常见风险。严格模式发现高风险项或未替换占位符时返回退出码 `1`；输入无法读取时返回 `2`。检查结果用于提醒人工复核，不能证明话术已经合规。

运行单元测试：

```bash
python3 -m unittest discover -s tests/live-selling-script -v
```

## 详细指南

- [Agent 执行说明](SKILL.md)
- [六步循环法](references/six-step-loop.md)
- [人群与痛点研究](references/discovery-routes.md)
- [平台与场景基线](references/platform-baselines.md)
- [产品事实、证据与风险边界](references/fact-evidence-compliance.md)
- [真人口语与观众体感](references/spoken-style.md)
- [阶段输出与交付格式](references/output-contracts.md)

## 方法来源

Skill 吸收了公开直播电商 Agent 与 Skill 中关于主播训练、平台适配、互动、FAQ、合规意识和按时间组织话术等通用实践：

- [Livestream Commerce Coach](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-livestream-commerce-coach.md)
- [China E-Commerce Operator](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-china-ecommerce-operator.md)
- [marketing-ecommerce-operator SKILL.md](https://github.com/treexxx/agent_skill/blob/main/skills/marketing-ecommerce-operator/SKILL.md)
- [TK 直播话术生成器](https://xiaping.coze.com/skill/78a4146b-cfdd-4fd4-9ff0-9223b4b46f95)

本项目自己的方法整合重点是六步循环、阶段式共创、产品事实先于营销主张、证据先于形容词，以及从观众体感出发的口语验收；同时主动避开高压催单、虚假稀缺和未经核验的行业数字。

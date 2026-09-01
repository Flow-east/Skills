# Flow-east Skills

这个仓库收录可供 Codex 及其他兼容 Agent 使用的个人 Skills。

## Skill 列表

| Skill | 用途 | 目录 |
| --- | --- | --- |
| `feishu-doc-permission` | 校验飞书文档写入内容，并在创建文档后自动授予协作者编辑权限 | [`feishu-doc-permission/`](feishu-doc-permission/) |
| `live-selling-script` | 通过阶段式共创，创作、审核和打磨有事实边界的中文直播成交话术 | [`live-selling-script/`](live-selling-script/) |
| `vpn-git-handoff` | 在切换 VPN 会导致 Agent 断线时，生成人工可执行的 Git 联网操作卡并负责切换前后的本地处理 | [`vpn-git-handoff/`](vpn-git-handoff/) |

## 安装

### 让 Codex 安装

安装共创式直播话术 Skill：

```text
请安装这个 skill：
https://github.com/Flow-east/Skills/tree/main/live-selling-script
```

安装飞书文档权限 Skill：

```text
请安装这个 skill：
https://github.com/Flow-east/Skills/tree/main/feishu-doc-permission
```

安装 VPN Git 交接 Skill：

```text
请安装这个 skill：
https://github.com/Flow-east/Skills/tree/main/vpn-git-handoff
```

安装完成后，在下一轮 Codex 对话中使用。

### 使用 Skills CLI

如果本机已经安装兼容的 Skills CLI：

```bash
npx skills add Flow-east/Skills --skill live-selling-script
npx skills add Flow-east/Skills --skill feishu-doc-permission
npx skills add Flow-east/Skills --skill vpn-git-handoff
```

### 手动安装到 Codex

```bash
git clone https://github.com/Flow-east/Skills.git floweast-skills
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R floweast-skills/live-selling-script \
  "${CODEX_HOME:-$HOME/.codex}/skills/live-selling-script"
```

将最后一条命令中的目录名替换为 `feishu-doc-permission` 或 `vpn-git-handoff`，即可安装对应 Skill。

## VPN Git Handoff

`vpn-git-handoff` 适用于只能通过公司 VPN 或受限网络访问 Git 远端，而切换网络会导致编程 Agent 断线的场景。

它把网络切换作为明确的人机边界：Agent 负责检查仓库、决定 Git 策略、完成本地修改和测试，并生成自包含操作卡；人负责切换网络、逐条执行卡片中的联网命令、保存输出并切回网络。`fetch`、`push` 和 `clone` 在 VPN 窗口执行，合并、变基和冲突处理留给 Agent 恢复连接后完成。

使用示例：

```text
使用 $vpn-git-handoff，为当前项目准备下一次 VPN Git 交接。
```

详细说明：

- [中文 README](vpn-git-handoff/README.zh-CN.md)
- [English README](vpn-git-handoff/README.md)

## Live Selling Script

`live-selling-script` 是一个面向中文直播场景的共创式 Skill。

它不会拿固定模板直接套产品，而是先与用户逐阶段研究产品事实、目标人群、真实痛点、平台调性、主播声音、现场证据、活动权益和成交路径；结构确认后，再使用六步循环法生成可说、可演示、可成交且有事实边界的直播话术。

### 核心方法

```text
产品事实核验
→ 目标人群与痛点共创
→ 平台和主播声音
→ 证据、演示、异议与权益
→ 六步结构确认
→ 完整逐字稿
→ 事实、口语和成交验收
```

六步循环法：

```text
拉新进场
→ 痛点信任
→ 方法交付
→ 互动确认
→ 痛点延伸
→ 行动指令
```

六步逻辑保持稳定，具体人群、痛点、证据、篇幅和成交动作根据产品与平台实时研究。

### 能做什么

- 从零共创直播带货或直播成交话术。
- 根据产品资料、商品页、截图和历史话术建立事实边界。
- 将视频或音频转写整理为忠实原话、结构分析和可用话术。
- 审核已有话术中的事实错误、证据缺失、书面感、AI 味和虚假承诺。
- 将同一产品适配到视频号、抖音、淘宝直播、快手或比赛演示场。
- 输出逐字稿、主播动作、画面演示、场控提示、互动分支和下一轮重开句。
- 检查绝对承诺、虚假稀缺、无依据数字和未替换占位符。

### 设计边界

- 不把行业常见痛点当成本产品用户的既定事实。
- 不从品类经验推断价格、库存、售后、效果和用户结果。
- 不默认使用“别走”“先别划走”、虚假倒计时或强逼单。
- 不把软件草稿、课程学习或服务过程夸成最终结果保证。
- 不用自动检查替代产品核验、法律判断和平台当前规则查询。

### 使用示例

```text
使用 $live-selling-script，和我共创一份虚拟直播间搭建服务的话术。
不要直接写稿，先盘点现有资料和未知信息。
```

```text
使用 $live-selling-script 审核这份小光鸟直播话术。
先查产品事实和无法兑现的承诺，不要先改写。
```

```text
使用 $live-selling-script，把这段比赛视频转写整理成原话、结构评价和改写建议。
听不清的地方要标出来，不要猜。
```

也可以自然触发：

```text
帮我写一份视频号直播卖课的话术，我们先把目标人群和课程交付研究清楚。
```

### 共创方式

Skill 默认不会一次抛出一张大问卷，而是：

1. 先读取已有文件、链接、截图、转写和历史结论。
2. 输出当前结论、推断依据和未知信息。
3. 每阶段只提出一到三个会影响下一步的问题。
4. 给出候选判断，让用户更容易校正。
5. 产品、人群、平台、证据和六步结构确认后，再展开完整逐字稿。

用户明确要求直接成稿时，Skill 会进入快速模式，并将假设和占位符写清楚。

### 输入建议

资料越真实，成稿越可靠。可以提供：

- 产品说明、商品页或真实界面。
- 价格、版本、权益、库存、交付和售后政策。
- 目标平台、账号阶段和本场目标。
- 主播视频、历史口播或明确的语言偏好。
- 用户评论、售前问题、售后问题和真实案例。
- 实物、截图、演示、资质或来源证据。
- 现有话术、音频、视频、转写或复盘报告。

缺少非关键资料时可以继续共创；缺少价格、效果、库存、售后等关键事实时，Skill 会保留明确占位符。

### 典型输出

- 产品事实卡。
- 人群痛点地图。
- 平台与主播声音卡。
- 卖点、证据、演示和异议地图。
- 六步结构卡。
- 5-10 分钟单品循环逐字稿。
- 主播动作、场控提示和互动分支。
- 下一轮重新进场句。
- 未确认信息与风险清单。

### 话术风险检查

检查脚本只使用 Python 标准库：

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md
```

输出 JSON：

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md --json
```

严格模式会在发现高风险承诺或未替换占位符时返回退出码 `1`：

```bash
python3 live-selling-script/scripts/lint_script.py path/to/script.md --strict
```

## Feishu Document Permission

`feishu-doc-permission` 用于飞书文档自动化的两项保护：

1. 文档创建或更新前，拒绝空内容和无意义内容。
2. 文档创建后，通过飞书开放平台为指定协作者授予编辑权限。

显式调用示例：

```text
使用 $feishu-doc-permission 检查这份飞书文档内容，并在创建后给指定用户编辑权限。
```

详细流程、参数和错误处理见 [`feishu-doc-permission/SKILL.md`](feishu-doc-permission/SKILL.md)。

## 开发与验证

运行直播话术检查脚本的单元测试：

```bash
python3 -m unittest discover -s tests/live-selling-script -v
```

使用 Codex 自带的 Skill Creator 校验全部 Skill：

```bash
for skill in feishu-doc-permission live-selling-script vpn-git-handoff; do
  python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

## 仓库结构

```text
.
├── README.md
├── LICENSE
├── feishu-doc-permission/
│   ├── SKILL.md
│   └── scripts/
├── live-selling-script/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── references/
│   │   ├── discovery-routes.md
│   │   ├── fact-evidence-compliance.md
│   │   ├── output-contracts.md
│   │   ├── platform-baselines.md
│   │   ├── six-step-loop.md
│   │   └── spoken-style.md
│   └── scripts/
│       └── lint_script.py
├── vpn-git-handoff/
│   ├── README.md
│   ├── README.zh-CN.md
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   └── references/
│       └── manual-vpn-git-sop.md
└── tests/
    └── live-selling-script/
```

## 方法来源与吸收原则

直播话术 Skill 吸收了公开直播电商 Agent/Skill 中关于主播训练、平台差异、产品顺序、互动、FAQ、合规和分钟级脚本的通用方法，同时避免照搬高压催单、虚假稀缺和未经核验的行业数字。

公开参考：

- [Livestream Commerce Coach](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-livestream-commerce-coach.md)
- [China E-Commerce Operator](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-china-ecommerce-operator.md)
- [marketing-ecommerce-operator SKILL.md](https://github.com/treexxx/agent_skill/blob/main/skills/marketing-ecommerce-operator/SKILL.md)
- [TK 直播话术生成器](https://xiaping.coze.com/skill/78a4146b-cfdd-4fd4-9ff0-9223b4b46f95)

项目自己的核心方法是：六步循环、阶段式共创、产品事实优先、证据先于形容词，以及真实观众体感下的口语验收。

## License

除非个别文件另有说明，本仓库全部内容采用 [MIT License](LICENSE)。

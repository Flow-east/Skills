# Flow-east Skills

[English](README.md) | **简体中文**

这个仓库收录可供 Codex 及其他兼容 Agent Skills 目录格式的编程智能体使用的可复用技能。

## Skills

| Skill | 版本 | 能做什么 | 适合场景 | 详细说明 |
| --- | --- | --- | --- | --- |
| `mac-mail-management` | [v0.1.0](https://github.com/Flow-east/Skills/blob/mac-mail-management-v0.1.0/mac-mail-management/README.zh-CN.md) | 通过 Mac 邮件 App 查信、起草和回复，附本地简历按授权发送，并防止重复投递。 | QQ/Gmail 邮件整理、简历投递及 Mac 上的定时邮件工作流。 | [中文说明](mac-mail-management/README.zh-CN.md) |
| `prompt-assistant` | [v0.1.0](https://github.com/Flow-east/Skills/blob/prompt-assistant-v0.1.0/prompt-assistant/README.zh-CN.md) | 帮助创作与诊断提示词，积累有范围的偏好、案例、实际反馈和经验证的个人方法。 | 跨工具 Prompt、图像与视频指令、反复优化，以及在使用中学习。 | [中文说明](prompt-assistant/README.zh-CN.md) |
| `feishu-doc-permission` | [v0.1.0](https://github.com/Flow-east/Skills/blob/feishu-doc-permission-v0.1.0/feishu-doc-permission/README.zh-CN.md) | 在写入飞书文档前校验内容，并在创建后授予协作者编辑权限。 | 需要避免空文档和权限遗漏的飞书文档自动化。 | [中文说明](feishu-doc-permission/README.zh-CN.md) |
| `live-selling-script` | [v0.1.0](https://github.com/Flow-east/Skills/blob/live-selling-script-v0.1.0/live-selling-script/README.zh-CN.md) | 共创、审核和改写有事实与证据边界的中文直播成交话术。 | 直播逐字稿、产品演示、异议处理、平台适配和转写改稿。 | [中文说明](live-selling-script/README.zh-CN.md) |
| `vpn-git-handoff` | [v0.2.0](https://github.com/Flow-east/Skills/blob/vpn-git-handoff-v0.2.0/vpn-git-handoff/README.zh-CN.md) | 在切换 VPN 会导致编程智能体断线时，协调安全的 Git 交接，并可选择打开系统终端。 | 由人切换 VPN 完成 fetch、同步、push、clone 和失败恢复。 | [中文说明](vpn-git-handoff/README.zh-CN.md) |
| `koubo-editing` | [v0.3.0](https://github.com/Flow-east/Skills/blob/koubo-editing-v0.3.0/koubo-editing/README.zh-CN.md) | 分析口播内容、精剪原话，设计字幕、镜头与声音并输出有声成片。 | 中文口播短视频的结构设计与模板化剪辑。 | [中文说明](koubo-editing/README.zh-CN.md) · [English guide](koubo-editing/README.md) |

每个 Skill 都是独立完整的目录，并采用独立的语义化版本。“首次发布”日期链接到最早发布该 Skill 的仓库提交，Git Tag 标识版本快照。用户可先阅读对应 README；触发技能后，智能体会加载 `SKILL.md` 以及当前任务需要的相关资源。

## 安装

从上表选择一个 Skill 名称。

### 让兼容的智能体安装

将 Skill 的 GitHub 地址交给智能体，例如：

```text
请安装这个 Skill：
https://github.com/Flow-east/Skills/tree/main/vpn-git-handoff
```

### 使用 Skills CLI

如果当前环境提供兼容的 Skills CLI：

```bash
npx skills add Flow-east/Skills --skill vpn-git-handoff
```

将 `vpn-git-handoff` 替换为上表中的任意 Skill 名称即可。

### 手动安装到 Codex

```bash
git clone https://github.com/Flow-east/Skills.git floweast-skills
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R floweast-skills/vpn-git-handoff \
  "${CODEX_HOME:-$HOME/.codex}/skills/vpn-git-handoff"
```

安装其他 Skill 时，将复制命令中的源目录名和目标目录名同时替换为对应名称。

其他支持 `SKILL.md` 的智能体也可以使用同一技能目录；`agents/openai.yaml` 等智能体专用元数据在 Codex 之外通常是可选的。

## 开发与验证

使用 Codex 自带的 Skill Creator 校验全部 Skill：

```bash
for skill in feishu-doc-permission live-selling-script vpn-git-handoff prompt-assistant mac-mail-management koubo-editing; do
  python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

运行仓库单元测试：

```bash
python3 -m unittest discover -s tests/live-selling-script -v
python3 -m unittest discover -s tests/prompt-assistant -v
python3 -m unittest discover -s mac-mail-management/tests -v
python3 -m unittest discover -s koubo-editing/tests -v
node mac-mail-management/tests/test_driver.js
```

## 许可证

除非个别文件另有说明（口播剪辑技能中的字体与音效遵循其各自许可，见 `koubo-editing/THIRD_PARTY_NOTICES.md`），本仓库全部内容采用 [MIT License](LICENSE)。

# Flow-east Skills

[English](README.md) | **简体中文**

这个仓库收录可供 Codex 及其他兼容 Agent Skills 目录格式的编程智能体使用的可复用技能。

## Skills

| Skill | 版本 | 能做什么 | 适合场景 | 详细说明 |
| --- | --- | --- | --- | --- |
| `feishu-doc-permission` | [v0.1.0](https://github.com/Flow-east/Skills/blob/feishu-doc-permission-v0.1.0/feishu-doc-permission/README.zh-CN.md) | 在写入飞书文档前校验内容，并在创建后授予协作者编辑权限。 | 需要避免空文档和权限遗漏的飞书文档自动化。 | [中文说明](feishu-doc-permission/README.zh-CN.md) |
| `live-selling-script` | [v0.1.0](https://github.com/Flow-east/Skills/blob/live-selling-script-v0.1.0/live-selling-script/README.zh-CN.md) | 共创、审核和改写有事实与证据边界的中文直播成交话术。 | 直播逐字稿、产品演示、异议处理、平台适配和转写改稿。 | [中文说明](live-selling-script/README.zh-CN.md) |
| `vpn-git-handoff` | [v0.1.0](https://github.com/Flow-east/Skills/blob/vpn-git-handoff-v0.1.0/vpn-git-handoff/README.zh-CN.md) | 在切换 VPN 会导致编程智能体断线时，协调安全的 Git 操作。 | 由人切换 VPN 完成 fetch、同步、push、clone 和失败恢复。 | [中文说明](vpn-git-handoff/README.zh-CN.md) |

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
for skill in feishu-doc-permission live-selling-script vpn-git-handoff; do
  python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" "$skill"
done
```

运行仓库单元测试：

```bash
python3 -m unittest discover -s tests/live-selling-script -v
```

## 许可证

除非个别文件另有说明，本仓库全部内容采用 [MIT License](LICENSE)。

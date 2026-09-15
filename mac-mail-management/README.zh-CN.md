# mac邮件管理

[English](README.md) | **简体中文** · [← 返回全部 Skills](../README.zh-CN.md)

当前版本：[v0.1.0](https://github.com/Flow-east/Skills/blob/mac-mail-management-v0.1.0/mac-mail-management/README.zh-CN.md)

通过 macOS 自带的“邮件”App 管理已配置的 QQ、Gmail 等邮箱。技能显示名称为 **mac邮件管理**，目录名和英文调用名为 `mac-mail-management`。

## 能做什么

- 发现账户和文件夹，请求检查新邮件，分页查询邮件元数据。
- 阅读正文与附件信息，按要求标记已读或未读。
- 在本地预览邮件，保存新建草稿或原生回复，附上本地简历等文件。
- 核对发件账户、收件人、正文和附件，再将已授权的邮件提交给 Mail 发送。
- 持久保存发送记录，防止重复投递；结果不明确时停止自动重试。
- 指导智能体使用可用的调度工具，配置定时查信与已授权的简历投递流程。

## 使用条件

- Mac 上有 Apple Mail、Python 3 和系统自带的 `osascript`；运行脚本不需要安装 pip/npm 包。
- 目标邮箱已添加到 Mail，并能正常同步。凭据继续由 Mail 管理，技能不读取密码或 QQ 授权码。
- 执行脚本的进程需要正常的 macOS“控制邮件”自动化权限；智能体的执行沙盒也可能要求本机应用访问审批。

目录兼容 Agent Skills 格式，其他兼容智能体也可在 macOS 上加载。`agents/openai.yaml` 是可选的 Codex 界面元数据；Node.js 仅用于运行驱动模拟测试。

## 安装

让兼容的智能体安装：

```text
请安装这个 Skill：
https://github.com/Flow-east/Skills/tree/main/mac-mail-management
```

也可在仓库副本中复制完整目录到 Codex 的个人技能目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R mac-mail-management "${CODEX_HOME:-$HOME/.codex}/skills/mac-mail-management"
```

## 使用示例

```text
用 mac邮件管理，总结 QQ 收件箱里的未读招聘邮件。
```

```text
使用 $mac-mail-management，按我提供的收件人起草求职邮件，附上我选定的简历。
```

智能体会先发现真实账户 ID 和文件夹路径，再处理邮件。具体命令和 JSON 请求格式见[操作说明](references/operations.md)。

## 发送与主动工作流

发送需要明确的用户指令，或已有且适用的授权规则。授权可以覆盖一批投递，不要求逐封再次确认。安装技能本身不会启用自动发送，也不会创建定时任务。

CLI 在发送前核对草稿，并将状态保存到 `~/Library/Application Support/mac-mail-management`。这些私人记录包含收件人和草稿正文，不应上传到公开仓库。重试与定时运行须沿用同一状态目录及任务标识。

`submitted_to_mail` 只表示 Mail 接受发送请求，不代表收件人已收到。结果不明确时停止自动重试。本地定时工作依赖 Mac、Mail 和调度器可运行，不能保证电脑休眠或关机时仍执行。

## 范围与验证

- 本版没有内置下载收件附件、删除、转发或移动文件夹的命令。
- 邮件列表采用 Mail 原生顺序，不保证最新邮件排在前面；过滤作用于当页扫描范围，部分扫描必须按部分结果报告。
- Mail 可能更换草稿 ID，或无法直接枚举编辑中的附件。脚本核对可用的附件路径，或唯一匹配已保存草稿并验证实际附件字节；核验失败就停止。发送期间不要同时编辑同一草稿。
- 已实测账户/文件夹访问，以及带附件的临时草稿；测试没有真实发送邮件。

在仓库根目录运行离线测试：

```bash
python3 -m unittest discover -s mac-mail-management/tests -v
node mac-mail-management/tests/test_driver.js
```

Python 测试覆盖请求校验、草稿变化、附件核验、授权标记、并发、防重复投递和发送状态不明等情况。Node 测试使用模拟 Mail 驱动；两组测试均不会发送邮件。

## 详细说明

- [智能体执行说明](SKILL.md)
- [命令、请求与故障处理](references/operations.md)
- [主动查信和投递流程](references/automation.md)

## 许可证

沿用仓库的 [MIT 许可证](../LICENSE)。

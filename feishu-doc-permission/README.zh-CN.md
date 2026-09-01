# 飞书文档内容与权限保护

[English](README.md) | **简体中文** · [← 返回全部 Skills](../README.zh-CN.md)

当前版本：[v0.1.0](https://github.com/Flow-east/Skills/blob/feishu-doc-permission-v0.1.0/feishu-doc-permission/README.zh-CN.md) · 发布日期：2026-09-01

`feishu-doc-permission` 为飞书文档自动化增加两道保护：写入前校验待发送内容，文档创建后为指定协作者授予访问权限。

这个 Skill 提供智能体工作流和三个轻量 Python 脚本；真正的文档创建或更新仍由你的飞书工具、API 客户端或自动化程序完成。

## 适用场景

- 自动化程序创建或更新飞书文档，需要在发送前拒绝空内容。
- 新建文档需要立即向指定同事开放编辑权限，避免再手动分享。
- 封装飞书文档 API 时，希望统一执行内容和权限检查。

它不适合代替飞书界面的手动分享，也不负责非飞书文件、应用配置、协作者身份查询，或权限查询与撤销等完整权限生命周期管理。

## 能力与边界

- **内容预检：**校验行内文本或 UTF-8 文件，去除首尾空白后可按最小长度拦截。它不会判断内容是否真实、有用或语义完整。
- **租户令牌获取：**使用飞书自建应用的 App ID 和 App Secret 换取 `tenant_access_token`。脚本可把结果写入缓存文件，但不会自动读取或刷新该缓存。
- **权限授予：**为指定协作者授予 `view`、`edit` 或 `full_access`，默认是 `edit`。支持 `docx`、`doc`、`sheet`、`folder`、`mindnote`、`slides` 和 `wiki` 类型的令牌。
- **飞书前置条件：**调用方需要事先拿到文档令牌和协作者 ID；飞书应用也必须具备所需权限范围，并能访问目标文档。
- **流程责任：**应校验真正准备写入的同一份内容。这些脚本无法确认另一个工具随后是否原样发送了它。

App Secret 和租户令牌都属于敏感信息。令牌脚本会把令牌输出到标准输出，请避免将其写入共享终端日志，并妥善保护生成的缓存文件。

## 安装

使用兼容的 Skills CLI：

```bash
npx skills add Flow-east/Skills --skill feishu-doc-permission
```

也可以把完整的 `feishu-doc-permission` 目录复制到智能体的 Skills 目录，并让 `SKILL.md` 与 `scripts/` 保持在同一技能目录内。安装到个人 Codex 环境：

```bash
cp -R feishu-doc-permission "${CODEX_HOME:-$HOME/.codex}/skills/feishu-doc-permission"
```

## 最短调用示例

```text
使用 $feishu-doc-permission，在写入前校验这份飞书文档，并在创建后给 OpenID 为 ou_xxxx 的协作者编辑权限。
```

请提供最终内容或文件路径、文档类型和协作者标识。执行权限步骤时，还需要已经授权的飞书应用凭证或现成的租户令牌。

## 脚本与输入概览

三个脚本均使用 Python 3，且只依赖 Python 标准库。

| 脚本 | 主要输入 | 作用 |
| --- | --- | --- |
| [`scripts/check_content.py`](scripts/check_content.py) | `--content` 或 `--file` 二选一；可选 `--min-length` | 当去除首尾空白后的内容短于要求时终止流程。 |
| [`scripts/get_tenant_token.py`](scripts/get_tenant_token.py) | `--app-id`、`--app-secret`；可选 `--cache`、`--print-only` | 获取飞书租户令牌，并可将其写入 JSON 文件供外层流程使用。 |
| [`scripts/grant_edit_permission.py`](scripts/grant_edit_permission.py) | `--doc-token`、`--tenant-token`，再加 `--member-id` 或一个/多个 `--member` JSON 对象 | 调用飞书批量成员接口授予指定权限。 |

推荐执行顺序：

```text
校验内容 → 使用你的飞书工具创建或更新 → 获取文档令牌
         → 获取租户令牌 → 授予协作者权限
```

如果飞书返回 `403` 或 `1063002`，先确认应用已添加到目标文档，并已开通 `docs:permission.member:create` 权限。

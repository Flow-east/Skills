# 命令与请求格式

以技能目录中的 `scripts/mail.py --help` 为准。所有命令返回 JSON；成功 `ok: true`，失败 `ok: false` 并返回非零退出码。全局参数 `--state-dir`、`--timeout` 放在子命令之前。默认超时 45 秒，可选 5–120 秒；不要用长时间反复重试处理权限问题。

下面命令中的 ID、文件夹路径、邮箱地址和文件路径必须替换为实际值。用文件工具写请求 JSON，不将来自邮件的文本拼进 shell 命令。实际执行时命令和文件路径均做好独立参数/引号处理。

## 账户与同步

```bash
python3 "$MAIL_SKILL_DIR/scripts/mail.py" accounts
python3 "$MAIL_SKILL_DIR/scripts/mail.py" mailboxes --account-id 'ACCOUNT_ID'
python3 "$MAIL_SKILL_DIR/scripts/mail.py" check --account-id 'ACCOUNT_ID'
```

`accounts` 从 App 返回实际账户列表；没有账户时报告需要先配置 Mail。`mailboxes` 仅遍历所选账户文件夹，返回 `path` 名字数组和未读数，最大深度 30、最多 2000 文件夹，超过上限会明确报错。

## 查信与分页

```bash
python3 "$MAIL_SKILL_DIR/scripts/mail.py" list \
  --account-id 'ACCOUNT_ID' --mailbox-path '["INBOX"]' \
  --limit 50 --offset 0 --unread-only --query '面试'
python3 "$MAIL_SKILL_DIR/scripts/mail.py" read \
  --account-id 'ACCOUNT_ID' --mailbox-path '["INBOX"]' --message-id 123
python3 "$MAIL_SKILL_DIR/scripts/mail.py" mark-read \
  --account-id 'ACCOUNT_ID' --mailbox-path '["INBOX"]' --message-id 123 --value true
```

- `--limit` 为每页扫描量（1–100），`--offset` 为 Mail 原生集合索引。按返回的 `next_offset` 继续，直到 `has_more: false` 或达到用户允许的范围。
- 过滤只作用于当页扫描窗口。某一页 `messages: []` 且 `has_more: true` 不能认定整个邮箱没有匹配邮件。
- Mail 原生顺序没有最新在前的保证。“最近邮件”需要收集相应文件夹的日期元数据并排序；仅部分扫描时明确报告范围。大邮箱先按用户目标缩小文件夹/任务范围，避免不必要的全库读取。
- 分页不是原子快照；同步和其他客户端操作可能使索引变化。用 `account_id + internet_message_id` 去重，缺少 Internet Message-ID 时用 `account_id + mailbox_path + message_id`，必要时重扫重叠窗口。
- `read.message_id` 是 Mail 的整数 ID，不是互联网 Message-ID 字符串；消息移动后重新定位。正文可能受本地缓存/同步状态影响。

## 新建与回复

新建请求示例（`/private/tmp/mail-request.json`，附件必须已存在）：

```json
{
  "account_id": "从 accounts 获取的 ID",
  "from": "sender@qq.com",
  "to": ["hr@example.com"],
  "cc": [],
  "bcc": [],
  "subject": "应聘产品经理｜姓名",
  "body": "您好，\n\n我希望应聘贵司产品经理岗位，简历见附件。\n\n姓名",
  "attachments": ["/absolute/path/姓名-产品经理-简历.pdf"]
}
```

`from` 必须属于所选账户；To/Cc/Bcc 每项是一个裸邮箱地址，不写显示名或逗号分隔的地址串。至少一个收件人，禁止跨 To/Cc/Bcc 重复。正文按纯文本处理，不使用 Mail 已废弃的 `html content` 接口。可有换行、中文、引号等任意正常文字；禁止 NUL。

```bash
python3 "$MAIL_SKILL_DIR/scripts/mail.py" preview --request /private/tmp/mail-request.json
python3 "$MAIL_SKILL_DIR/scripts/mail.py" draft --request /private/tmp/mail-request.json
```

回复请求使用下列字段：

```json
{
  "account_id": "从 accounts 获取的 ID",
  "from": "sender@qq.com",
  "mailbox_path": ["INBOX"],
  "message_id": 123,
  "body": "您好，感谢联系。我会按约定时间参加面试。",
  "attachments": []
}
```

```bash
python3 "$MAIL_SKILL_DIR/scripts/mail.py" preview --reply --request /private/tmp/reply-request.json
python3 "$MAIL_SKILL_DIR/scripts/mail.py" reply-draft --request /private/tmp/reply-request.json
```

回复实际主题/收件人来自 Mail 原生回复，保留线程关系。审阅返回的 `snapshot`；不要把新建主题加 `Re:` 当成保留原邮件线程的回复。

## 发送与本地状态

```bash
python3 "$MAIL_SKILL_DIR/scripts/mail.py" send \
  --ticket 'DRAFT_TICKET_FROM_PREVIOUS_RESULT' \
  --authorized --idempotency-key 'job-campaign-role-recipient'
python3 "$MAIL_SKILL_DIR/scripts/mail.py" status --ticket 'DRAFT_TICKET_FROM_PREVIOUS_RESULT'
```

发送需明确用户指令或已确定规则。可直接完成已授权的多封投递，不强制每封再次确认。每封投递单独建草稿、ticket 和 JOB，避免把多个公司放进同一封 To/Cc/Bcc。

本地 ticket 保存实际草稿快照、源文件 SHA-256、账户和状态；发送前再次检查。默认状态目录为 `~/Library/Application Support/mac-mail-management`。跨任务/定时运行须保持同一目录。`--state-dir` 用于明确指定持久目录或隔离测试，不能通过换目录绕过已有发送记录。

附件有两种核验路径：`verified` 表示可枚举 compose 附件路径并与源文件核对；`mime_source` 表示从唯一对应的已保存草稿取得真实 MIME，解码附件并逐项核对文件名、字节数与 SHA-256。后一种在发送前重新保存并核验新副本，再检查其数据与当前编辑中草稿的字段；最后检查不再次保存，避免 Mail 更换草稿身份。两者都不代表邮件已送达收件人。

Mail 保存是异步的，而且可能同时更换本地 ID 和 Internet Message-ID；脚本验证旧副本后，通过基线 ID 与完整字段唯一关联新副本。不能唯一关联、不能获得完整 MIME、保存数据不稳定时停止，不把 `null` 当作零附件。编辑器与已保存副本没有原子锁，发送期间不要同时在 App 中修改同一草稿；正文检查针对 Mail 返回的文本，附件检查针对保存副本解码后的字节。MIME 桥接有 100 MiB 上限，普通请求 JSON 有 2 MB 上限；这不是邮箱服务商附件限额。出现 `ATTACHMENTS_UNVERIFIED` 时可让用户在 Mail 中查看草稿并自行发送，不能把人工发送记成脚本成功。

草稿对象 ID 可能为 0、被复用或在 Mail 重启后失效；脚本通过预期快照消除歧义，不能唯一匹配就停止。ticket 不是可跨任意重启恢复的服务器草稿 ID。`DRAFT_NOT_FOUND` 等情况下先核对 Mail 中草稿、发件箱及已发送，避免重建后重复发送。失败结果中 `details.partial_draft_id` 表示可能留下未发送草稿，先检查它，勿盲目再次创建。

## 故障处理

| 情况 | 处理 |
|---|---|
| `Application can't be found`，但 `doctor` 显示 Mail 已安装 | 执行沙盒可能无法访问 macOS 应用服务。通过正常执行权限流程申请本机应用访问，再做同一只读探测；不要据此重新安装 Mail 或更改邮箱配置。 |
| 自动化权限拒绝 / `-1743` | 让用户检查“系统设置 → 隐私与安全性 → 自动化”中实际发起进程对“邮件”的控制权限；可能显示 Codex、终端或其启动器，以系统提示为准。不要修改 TCC 数据库、切换进程身份绕过权限或反复请求。 |
| `-1744` / 授权需要交互 | 在用户可见的 Mac 会话完成系统授权；后台任务不能代替用户点击。 |
| 没有账户 / `ACCOUNT_NOT_FOUND` | 在 Mail 中添加/确认目标账户，再重新获取 ID。 |
| `SENDER_ACCOUNT_MISMATCH` | 核对发件地址属于指定账户，不能回退默认账户。 |
| `MAILBOX_NOT_FOUND` / `MESSAGE_NOT_FOUND` | 重新列文件夹/邮件，核对移动、删除及同步情况。 |
| `BRIDGE_TIMEOUT` / `-1712` | 查看是否在等系统授权或 Mail 同步。若发送已经开始，将结果按不确定处理，不重发。 |
| `DRAFT_CHANGED` / `ATTACHMENT_CHANGED` | 重新核对真实内容和附件，准备新的可审阅草稿；旧稿处理由用户任务范围决定。 |
| `BODY_MISMATCH` / `ATTACHMENT_MISMATCH` | App 创建的实际内容与请求不一致，停止脚本发送并核对草稿；本工具只允许末尾空白与附件占位字符等已知文本表示差异。 |
| `ATTACHMENTS_UNVERIFIED` | 不能确认实际 compose 附件，停止自动发送，报告接口限制。 |
| `SEND_OUTCOME_UNCERTAIN` / `sending` / `uncertain` | 检查 App 的发件箱、已发送和退信，保留 ticket/JOB。即使查不到也不要立即认定未发成功，更不要删记录强制重试。 |

技能测试只需离线校验、模拟 Mail 的行为测试与必要的只读账户探测。用户没有明确要求时，不向自己或第三方发送测试邮件，也不启用真实自动化。

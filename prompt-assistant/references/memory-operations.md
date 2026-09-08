# 本地记忆操作

这份文件给执行 Skill 的 Agent 使用。用户只需自然表达，不需要操作数据库、填写 JSON 或记住命令。

## 定位与设置

从实际安装位置调用 `scripts/memory.py`，不要假设工作目录就是 Skill 目录。下文 `MEMORY` 代表这个脚本的绝对路径；命令中的条目 ID 均取自工具输出，不可猜测。Python 3.9+，只有标准库，无模型调用或网络请求。

```bash
python3 "$MEMORY" status
python3 "$MEMORY" init
python3 "$MEMORY" config --memory off
python3 "$MEMORY" config --teaching off
```

先 `status`；未初始化且任务需要持久积累时 `init`。这两步只做一次必要初始化，不必每轮重复。`config` 也能首次建立设置库，因而第一次使用就关闭记忆仍会生效。关闭记忆不删除旧数据；`context` 返回空结果，生成、反馈等学习写入被拒绝，查看、导出、忘记仍可用。“这次不要记”只跳过本轮读写，别永久关闭其他任务的记忆。记忆开启时也不要保存琐碎轮次。

目录优先级：`--data-dir` > `PROMPT_ASSISTANT_HOME` > Unix 的 `${XDG_DATA_HOME:-~/.local/share}/prompt-assistant`，Windows 的 `%LOCALAPPDATA%/prompt-assistant`。例如 macOS 默认 `~/.local/share/prompt-assistant/memory.sqlite3`。全局参数必须放在子命令之前：

```bash
python3 "$MEMORY" --data-dir /tmp/prompt-assistant-demo init
```

不把数据库放进 Skill 或公开仓库。脚本会拒绝 Skill 内目录；其他私有目录由宿主选择。写入失败时说明未保存，继续会话，不悄悄换位置。数据不是加密存储；遵守最少必要记录原则。

## 开始任务时检索

```bash
python3 "$MEMORY" context --query '封面 文字 留白' --project '小光鸟' --scenario '文生图' --tool '目标工具名'
python3 "$MEMORY" get ENTRY_ID
```

未知项目/场景/工具就省略相应参数。范围值精确匹配，复用已存名称，别为同一工具随意创建别名。`*` 表示明确适用于全部；省略某个检索范围不等于搜索该范围下的全部私有上下文。

检索先按范围过滤，再按语义键解决冲突（项目优先，其次场景、工具），最后依据关键词与更新时间返回摘要。中文采用字组召回；没有向量模型，不保证同义词召回。首次没找到可换关键词，或 `list` 后查原文。当前明确指令始终覆盖检索结果。

默认最多 12 条、摘要总计 9000 字符，可用 `--limit`、`--budget` 调整。超过预算整条省略，返回 `omitted`；关键偏好缺失时缩小检索范围或按 ID 读取，不能假装已读全。摘要没有完整 Prompt，用 `get` 取得原文。`accepted_prompt_only` 只能作表达参考，`pitfall` 是反例，`example` 仍须检查工具和证据。候选偏好与候选/待复核/已停用方法不参与默认检索。

## 保存精选条目

`record --input` 接受 JSON 文件或标准输入 `-`，支持单个对象或最多 100 个对象的原子批次。使用文件/带引号的 heredoc，避免把用户文字拼接成 shell 代码。宿主如有文件编辑工具，优先用它写临时 JSON；完成后按宿主规则处理临时文件。

```bash
python3 "$MEMORY" record --input - <<'JSON'
{
  "kind": "case",
  "key": "cover.bird.v1",
  "title": "小光鸟封面：保留手绘感",
  "body": "为小光鸟账号做无字封面，保留角色轮廓与手绘质感；尚未在目标工具试用。",
  "scope": {"project": "小光鸟", "scenario": "文生图", "tool": "*"},
  "source": "user_statement",
  "data": {
    "task_id": "bird-cover-001",
    "request": "想做一张封面，不要文字，沿用我提供的角色参考。",
    "prompt": "以附带角色图为参考，创作一张没有文字的封面。保留角色轮廓、配色和手绘笔触，让角色成为画面主体。背景采用浅色，并留出自然的呼吸空间。",
    "materials": ["需随提示词附带角色参考图；未把图片复制到数据库"],
    "parameters": {},
    "tool_version": "未指定"
  }
}
JSON
```

上述是合成示例，不自动导入任何人的真实记忆。记录用户案例时替换为真实事实，别沿用示例反馈。

共同字段：`kind/key/title/body/scope/source/data`。`body` 是紧凑、独立可懂的检索摘要，不是全部聊天记录；`key` 是稳定语义键；`related_ids` 可选，列出内容派生所依赖的已有 ID，便于更正、遗忘和证据追踪。保留历史依赖，不能通过改写丢掉私人来源。

| kind | data 与规则 |
| --- | --- |
| `case` | 必填 `task_id/request/prompt`；可附 `parent_id/materials/parameters/tool_version/output`。每次新建 `draft`，实质修订用同一 `task_id` 和上一版 `parent_id`。同一任务多版不算独立验证。 |
| `preference` | 用 `data.evidence` 留下用户原话或推测依据；`source: user_statement` 为明确偏好，`inference` 为暂定。相同 key + scope 更新原条目并留历史。 |
| `project` | 项目背景与长期要求；记录依据与有效时间。不要存凭据或整份无关材料。 |
| `learning` | 必填 `stage/evidence`；阶段是 `introduced/understood/applied`。后两者须用户报告、明确表达或可见应用证据。 |
| `method` | 必填 `rationale/when_not`，主体做法写在 `body`。每次新增或改写都为 `candidate`；`related_ids` 连接依据案例。 |

来源枚举：`user_statement`（用户明确表达）、`user_report`（用户报告结果）、`observation`（工具可见事实）、`inference`（推测）、`curated`（有出处的方法知识）、`assistant_explanation`（解释过的知识）。不能把推测伪装成用户偏好；工具也会拒绝用推测覆盖同键同范围的明确记录。需要保留另一个假设时单列暂定键，别创建一个更宽范围的假设来绕过已有偏好。

保存长期偏好的例子：

```json
{
  "kind": "preference",
  "key": "cover.text",
  "title": "小光鸟封面不放文字",
  "body": "小光鸟账号的封面默认不放文字；其他账号没有这条要求。",
  "scope": {"project": "小光鸟", "scenario": "文生图"},
  "source": "user_statement",
  "data": {"evidence": "用户明确说：这个账号以后的封面都不放文字。"}
}
```

## 记录认可和实际结果

```bash
python3 "$MEMORY" feedback CASE_ID --input feedback.json
```

```json
{
  "signal": "result_good",
  "source": "user_report",
  "evidence": "用户说已在目标工具试过，角色轮廓保住了，画面也符合预期。",
  "output": {"artifact": "用户未提供原图", "tool_version": "用户未说明"}
}
```

`prompt_accepted` 只认可提示词；`result_good/result_mixed/result_bad` 对应真实结果。必须有具体反馈和 `user_report/observation` 来源。后续再次认可提示词不会清除已有失败结果。每次反馈事件均保留；实际结果可因新证据改变。核对反馈指向的版本，不能一律关联最新版本。

如新案例验证的是现有方法，`related_ids` 连接该方法；出现失败时也在反馈里说明。这样反例能沿关系将方法置为 `review`。**工具目前自动处理的是支持该方法的旧案例改为失败**；新派生案例失败不意味着其所有上游方法都失效，Agent 须检查归因并对相关方法执行 `revoke` 或修订回候选。不可把自动传播说成完整因果诊断。

## 方法验证

```bash
python3 "$MEMORY" validate METHOD_ID --input trials.json
```

```json
{
  "conclusion": "两项任务中固定角色特征后，角色一致性均改善；仅用于该项目的参考图编辑。",
  "trials": [
    {
      "case_id": "实际有效案例A的ID",
      "verdict": "helpful",
      "source": "observation",
      "baseline_result": "原结果改变了角色耳朵轮廓。",
      "candidate_result": "修订后轮廓符合参考图。",
      "controls": "同一参考图、同一模型版本和设置；只改明确保留特征的描述。",
      "evidence": "实际检查两张产物的轮廓；记录可访问的产物引用。"
    },
    {
      "case_id": "另一个独立任务的有效案例ID",
      "verdict": "helpful",
      "source": "user_report",
      "baseline_result": "用户报告原结果配色偏离。",
      "candidate_result": "用户报告新结果保留配色。",
      "controls": "用户确认相同工具、版本与参考素材；只增加保留条件。",
      "evidence": "保留用户实际比较描述，不得把本例当成已完成的试验。"
    }
  ]
}
```

验证要求两个不同 `task_id` 的 `effective` 案例、相符范围、完整对照证据和 `helpful` 判定。已有直接关联的 `mixed/failed` 案例时，不能只选成功案例重新启用：还须提供 `counterexamples` 数组，每项含 `case_id/resolution/source/evidence`，逐条说明反例如何处理、方法有何限制，来源为 `user_report` 或 `observation`。

脚本检查这些字段和记录关系，**无法独立判断文字证据是否真实、对照是否充分**；这由 Agent 核对可见材料及用户报告。禁止凑数。没有结果证据就保持候选，不为收集反馈强制执行付费生成。

## 用户管理自己的积累

| 用户说 | 操作 |
| --- | --- |
| 你记住了什么 | `list`；按 `--kind`、`--state` 筛选；需要更多条目提高 `--limit` |
| 看以前满意的版本 | `context` 找相关案例，再 `get ID`；实际有效与仅认可分开说明 |
| 这条只用于这个项目 | `rescope ID --input scope.json`；文件如 `{"project":"小光鸟","scenario":"文生图"}`，未填项为 `*` |
| 这条偏好理解错了 | 同 key + scope 用 `record` 写明纠正依据 |
| 上次怎么改过 | `history ID` |
| 恢复第 N 版 | `rollback ID --revision N`；案例改用旧案例 ID，方法恢复后重新验证 |
| 别再用这个方法 | `revoke ID --reason '用户给出的停用原因'` |
| 整理一下经验 | `review` 查看候选、反例与待复核项；逐条检查，不批量自动批准 |
| 忘记这条 | 先 `impact ID` 查看派生范围，再 `forget ID`；明确授权且范围符合指令就执行，不重复询问 |
| 导出积累 | `export --output /私有目录/prompt-memory.json`；目标已存在会拒绝覆盖 |
| 换电脑恢复 | 在新目录 `init`，再 `import --input /私有目录/prompt-memory.json` |

`rescope` 输入是完整的新范围，所有省略项归为 `*`；如果只改项目，先 `get` 读出并保留原场景与工具。与已有同键记录冲突会停止，先辨别两条含义再处理。

导入仅支持空库、相同 schema，保留来源、历史和 ID；个人方法在新环境回到候选，已停用方法保持停用。关闭记忆的设置也随导入恢复。旧版不识别新 schema 时会报错，不能擅自重建覆盖。第一版未提供任意数据库的自动合并或跨 schema 迁移。

遗忘会一并清除数据库中的条目、历史、反馈及已关联派生内容，可能包含引用该内容的后续案例。没有标记关联的自由文本副本无法自动识别；在记录时维护 `related_ids`，发现遗漏时先找出相关条目。已有导出、系统备份、外部图片或宿主聊天记录不在删除范围内。

业务命令输出 JSON；失败退出码 2，成功 0。命令行语法错误由 argparse 给出用法说明。写入使用事务；同一批次失败不留下半批记录。不要将错误输出当成功，也不要仅在回复中说“记住了”而不实际调用工具。

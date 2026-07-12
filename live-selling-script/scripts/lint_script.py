#!/usr/bin/env python3
"""Flag common claim, scarcity, placeholder, and spoken-style risks in Chinese livestream scripts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str
    pattern: re.Pattern[str]
    message: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    line: int
    match: str
    message: str
    text: str


RULES = (
    Rule(
        "ABSOLUTE_PROMISE",
        "HIGH",
        re.compile(
            r"绝对|百分之百|100%|所有人都|任何问题都|永远(?:不|都|能)|永久(?:有效|免费|升级)|"
            r"适合所有人|任何人都能|零风险|无任何风险|保证(?:你|能|可以|一定)|"
            r"完全不用(?:改|学|管)|(?:根本|完全)看不出来|零学习成本|一键爆款"
        ),
        "绝对化或结果保证需要删除、降级，或补充明确证据与适用条件。",
    ),
    Rule(
        "RESULT_CLAIM",
        "HIGH",
        re.compile(r"买了就能(?:涨粉|变现)|保证(?:涨粉|变现|就业|成交)|爆款保证|包治|治愈"),
        "用户结果不能由中间能力直接推出，需核验资质、条件和证据。",
    ),
    Rule(
        "SUPERLATIVE",
        "VERIFY",
        re.compile(r"全网最低|史上最低|行业第一|国家级|世界级|最强|顶级|天花板"),
        "极限或地位主张需要当前、可比且可核验的依据。",
    ),
    Rule(
        "SCARCITY",
        "VERIFY",
        re.compile(r"只有今天|下播(?:就)?下架|库存(?:有限|告急)|仅剩\s*\d+|最后\s*\d+\s*(?:单|件|分钟)"),
        "稀缺性必须与真实库存、活动时间和后台机制一致。",
    ),
    Rule(
        "NUMERIC_OUTCOME",
        "VERIFY",
        re.compile(
            r"(?:提升|提高|降低|减少|节省|解决|转化率|效率)[^。！？\n]{0,24}"
            r"(?:\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*倍)"
        ),
        "数字效果需要来源、口径、时间范围和测试条件。",
    ),
    Rule(
        "PRICE_ANCHOR",
        "VERIFY",
        re.compile(r"(?:原价|日常价|官方价|门店价)\s*[¥￥]?\s*\d+"),
        "价格锚点需要真实销售记录或当前官方页面支持。",
    ),
    Rule(
        "COMMAND_HOOK",
        "STYLE",
        re.compile(r"别走|先别划走|听我说|听这一段|给我\s*\d+\s*分钟"),
        "命令式留人容易引起抗拒，优先改成相关场景或可见证明。",
    ),
)

PLACEHOLDER_RE = re.compile(r"\[[^\]\n]{1,80}\]|〔[^〕\n]{1,80}〕|\bTODO\b", re.IGNORECASE)
NEGATION_RE = re.compile(
    r"不(?:是|说|承诺|保证|代表)|不能说|不要说|不用(?:我)?说|避免|禁止|禁用|并非"
)
SKIP_HEADING_RE = re.compile(r"禁用|禁止|不要说|风险表达|话术红线|反例")
ACTION_PREFIX_RE = re.compile(
    r"^(?:主播动作|画面|场控|动作|演示|先展示|展示|切换|点击|打开|输入|现场|靠近|依次|"
    r"拿起|读评论|等待|生成)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检查中文直播话术中的承诺、稀缺、数字、占位符和口语风险。"
    )
    parser.add_argument("path", type=Path, help="要检查的 Markdown 或纯文本文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="存在 HIGH 风险或未替换占位符时返回退出码 1",
    )
    return parser.parse_args()


def heading_level(line: str) -> int | None:
    match = re.match(r"^(#{1,6})\s+", line)
    return len(match.group(1)) if match else None


def collect_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    skipped_section_level: int | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        level = heading_level(line)

        if level is not None:
            if skipped_section_level is not None and level <= skipped_section_level:
                skipped_section_level = None
            if SKIP_HEADING_RE.search(line):
                skipped_section_level = level
            continue

        if not line or skipped_section_level is not None:
            continue

        for match in PLACEHOLDER_RE.finditer(line):
            candidate = match.group(0)
            inner = candidate[1:-1].strip() if candidate.startswith("[") else candidate
            if candidate.startswith("[") and ACTION_PREFIX_RE.search(inner):
                continue
            findings.append(
                Finding(
                    code="PLACEHOLDER",
                    severity="PLACEHOLDER",
                    line=line_number,
                    match=candidate,
                    message="发布或上播前确认并替换占位信息。",
                    text=line,
                )
            )

        for rule in RULES:
            for match in rule.pattern.finditer(line):
                context_start = max(0, match.start() - 12)
                context = line[context_start : match.end()]
                severity = "REVIEW" if NEGATION_RE.search(context) else rule.severity
                message = (
                    "该表达出现在否定或边界说明中，请人工确认无需改动。"
                    if severity == "REVIEW"
                    else rule.message
                )
                findings.append(
                    Finding(
                        code=rule.code,
                        severity=severity,
                        line=line_number,
                        match=match.group(0),
                        message=message,
                        text=line,
                    )
                )

        if (
            len(line) >= 110
            and not line.startswith(("-", "*", ">", "|", "["))
            and not re.match(r"^\d+[.、]", line)
        ):
            findings.append(
                Finding(
                    code="LONG_SPOKEN_LINE",
                    severity="STYLE",
                    line=line_number,
                    match=f"{len(line)} chars",
                    message="长段落可能偏书面，朗读后按自然停顿拆分。",
                    text=line,
                )
            )

    return findings


def render_text(path: Path, findings: list[Finding]) -> str:
    if not findings:
        return f"OK {path}: 未发现内置规则覆盖的明显风险。"

    counts = Counter(item.severity for item in findings)
    summary = ", ".join(f"{severity}={count}" for severity, count in sorted(counts.items()))
    lines = [f"CHECK {path}: {len(findings)} findings ({summary})"]
    for item in findings:
        lines.append(
            f"L{item.line} [{item.severity}] {item.code}: {item.match} - {item.message}\n"
            f"  {item.text}"
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: 无法读取 {args.path}: {exc}", file=sys.stderr)
        return 2

    findings = collect_findings(text)
    if args.json:
        payload = {
            "path": str(args.path),
            "count": len(findings),
            "findings": [asdict(item) for item in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.path, findings))

    if args.strict and any(item.severity in {"HIGH", "PLACEHOLDER"} for item in findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

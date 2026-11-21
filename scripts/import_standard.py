#!/usr/bin/env python3
"""Import numbered G.* clauses from a Markdown SQL standard.

The generated common catalog is a traceability baseline. Dialect-specific
details live in mysql.json and postgresql.json and are maintained separately.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


LEVEL_TERMS = {
    "prohibition": ("禁止", "严禁", "不允许", "不得", "不能"),
    "recommendation": ("建议", "避免", "不宜", "优先", "尽量", "不要"),
}

STATIC_IDS = {
    "G.TAB.04", "G.TAB.05", "G.TAB.09", "G.TAB.10", "G.TAB.13", "G.TAB.16",
    "G.IDX.08", "G.IDX.09", "G.IDX.10", "G.IDX.11", "G.FMT.02", "G.FMT.05",
    "G.FMT.07", "G.NAM.02", "G.NAM.03", "G.NAM.09", "G.CMT.08", "G.CMT.09",
    "G.SEL.08", "G.SEL.12", "G.SEL.21", "G.SEL.25", "G.SEL.31", "G.INS.01",
    "G.DEL.01", "G.UPD.01", "G.UPD.02", "G.UPD.03", "G.UPD.05", "G.TXN.01",
    "G.TXN.03", "G.TXN.07", "G.UPG.03", "G.UPG.05", "G.UPG.06", "G.UPG.07",
    "G.UPG.08", "G.UPG.10", "G.UPG.11", "G.KOO.04", "G.KOO.06",
}

MANUAL_PREFIXES = {"DBS", "CLI", "SEC", "KOO"}
CONFIRM_PREFIXES = {"TAB", "IDX", "UPG"}
CONFIRM_IDS = {"G.DEL.02", "G.UPG.09"}
REFERENCE_IDS = {"G.FMT.08"}
RECOMMENDATION_IDS = {"G.IDX.09", "G.IDX.10"}

PORTABLE_OVERRIDES = {
    "G.DBS.01": "客户端与服务端必须统一使用目标数据库支持的 Unicode 编码；具体编码由方言规则给出。",
    "G.DBS.04": "单个数据库实例不得超过项目批准的容量预算；必须结合托管平台上限、备份恢复时间和扩容策略评审。",
    "G.DBS.05": "实例、数据库、表和字段的排序规则必须统一管理；需要二进制或语言排序时单独评审。",
    "G.TAB.01": "新表必须使用目标数据库推荐且支持事务、崩溃恢复的表实现；具体要求由方言规则给出。",
    "G.TAB.05": "表和字符字段必须使用目标数据库的统一 Unicode 编码策略。",
    "G.TAB.15": "时间字段必须根据是否表示绝对时间点、是否需要时区转换来选择类型；具体类型由方言规则给出。",
    "G.IDX.06": "避免直接索引大文本或超长字段；确需检索时使用目标数据库支持的表达式、全文或专用索引。",
    "G.IDX.11": "新表禁止使用数据库本地自增序列作为分布式主键；优先使用有时序的 UUID，并采用方言原生高效类型。",
    "G.SEL.03": "禁止对大文本或超长字符串直接执行排序、去重等高成本操作；阈值和替代索引能力按目标数据库评估。",
    "G.UPD.03": "批量更新必须按稳定键确定处理范围；禁止依赖不确定行集的顶层行数限制语法控制修改数量。",
    "G.TXN.07": "未经架构与运维批准，禁止使用跨资源分布式事务；具体协议和替代方案按目标数据库与平台评审。",
    "G.UPG.12": "生产环境创建索引必须采用目标数据库支持的在线/并发方式，并评估锁影响。",
    "G.UPG.04": "删除分区时必须按目标数据库能力维护所有受影响索引；不得跨方言照搬全局索引语法。",
    "G.TAB.18": "三年预期超过一千万行的表必须评估分区或分库分表；有时间清理特征的表优先评估分区，其他大表评估项目批准的分片平台。",
    "G.KOO.01": "开发阶段必须归档增量升级 SQL，并与已批准的数据模型设计保持一致。",
    "G.KOO.02": "版本封版后必须按基线、升级、回滚和可选环境定制四类目录归档 SQL；文件名和执行顺序必须可确定。",
    "G.KOO.05": "修改项目声明的系统配置表时，必须显式写出环境级配置标志，不得依赖隐式默认值。",
    "G.KOO.06": "禁止删除表、字段及项目声明的受保护配置数据。",
    "G.KOO.07": "使用平台加密组件写入的数据必须验证能够按授权路径正确解密。",
    "G.KOO.09": "设计阶段完成表设计后，必须执行项目批准的数据模型规范检查。",
}

NAME_OVERRIDES = {
    "G.DBS.01": "客户端与服务端统一使用目标数据库支持的 Unicode 编码",
    "G.DBS.04": "数据库实例容量不得超过项目批准预算",
    "G.DBS.05": "实例、数据库、表与字段排序规则统一管理",
    "G.TAB.01": "新表使用目标数据库推荐的事务型表实现",
    "G.TAB.05": "表与字符字段使用统一 Unicode 编码策略",
    "G.TAB.15": "按绝对时间点与本地时间语义选择时间类型",
    "G.TAB.18": "超大表必须评估分区或分片",
    "G.IDX.06": "大文本与超长字段使用目标数据库适配的索引方案",
    "G.IDX.11": "分布式主键禁止依赖数据库本地自增序列",
    "G.SEL.03": "禁止对大文本或超长字符串直接排序去重",
    "G.UPD.03": "批量更新必须按稳定键确定处理范围",
    "G.TXN.07": "未经批准禁止跨资源分布式事务",
    "G.UPG.04": "删除分区时按目标数据库能力维护受影响索引",
    "G.UPG.12": "生产索引变更使用目标数据库在线或并发能力",
    "G.KOO.01": "开发阶段归档增量升级 SQL 并与批准的数据模型一致",
    "G.KOO.02": "版本封版后按基线、升级、回滚和环境定制目录归档",
    "G.KOO.05": "系统配置变更显式声明环境级配置标志",
    "G.KOO.06": "禁止删除结构和受保护配置数据",
    "G.KOO.07": "加密数据必须验证授权解密路径",
    "G.KOO.09": "表设计必须执行批准的数据模型规范检查",
}


def clean(value: str) -> str:
    value = re.sub(r"!\[[^]]*]\([^)]*\)", "", value)
    value = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>|&nbsp;", " ", value)
    value = re.sub(r"[`*_\\]", "", value)
    value = re.sub(r"\s+", " ", value).strip(" #:-")
    return value


def level_for(clause_id: str, text: str) -> str:
    if clause_id in REFERENCE_IDS:
        return "reference"
    if clause_id in RECOMMENDATION_IDS:
        return "recommendation"
    for level, terms in LEVEL_TERMS.items():
        if any(term in text for term in terms):
            return level
    return "mandatory"


def gate_for(level: str) -> str:
    return "block" if level in {"prohibition", "mandatory"} else "warn" if level == "recommendation" else "info"


def expand_id(raw_id: str) -> list[str]:
    match = re.fullmatch(r"(G\.[A-Z]+\.)([0-9]+)(?:/([0-9]+))?", raw_id)
    if not match:
        return []
    ids = [match.group(1) + match.group(2)]
    if match.group(3):
        ids.append(match.group(1) + match.group(3))
    return ids


def parse_clauses(markdown: str) -> list[dict[str, object]]:
    heading = re.compile(r"^(#{3,4})\s+(?:\*\*)?(G\.[A-Z]+\.[0-9]+(?:/[0-9]+)?)(.*)$", re.MULTILINE)
    matches = list(heading.finditer(markdown))
    clauses: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = clean(match.group(3))
        body = markdown[match.end():body_end]
        prose = []
        for line in body.splitlines():
            stripped = clean(line)
            if not stripped or line.lstrip().startswith(("|", "```", "* ", "- ")):
                continue
            prose.append(stripped)
            if sum(map(len, prose)) >= 420:
                break
        for clause_id in expand_id(match.group(2)):
            prefix = clause_id.split(".")[1]
            name = NAME_OVERRIDES.get(clause_id) or title or clause_id
            # Severity follows the source clause wording, not the portable display name.
            level = level_for(clause_id, title or name)
            condition = PORTABLE_OVERRIDES.get(clause_id) or name
            if prose and clause_id not in PORTABLE_OVERRIDES:
                condition = f"{condition}。{' '.join(prose)}"[:700]
            kind = "static" if clause_id in STATIC_IDS else "manual" if prefix in MANUAL_PREFIXES else "hybrid"
            clauses.append({
                "id": clause_id,
                "source": [clause_id],
                "name": name,
                "level": level,
                "gate": gate_for(level),
                "scope": [prefix.lower()],
                "dialects": ["mysql", "postgresql"],
                "condition": condition,
                "check": {
                    "kind": kind,
                    "detector": "静态解析 SQL/代码并结合 schema 判断。" if kind == "static" else
                                "静态筛查候选项，并结合 schema、执行计划或业务语义确认。" if kind == "hybrid" else
                                "核对设计、运行数据、审批或运维证据。",
                },
                "examples": {
                    "positive": f"满足“{name}”并保留可核验证据。",
                    "negative": f"违反“{name}”或缺少所需证据。",
                },
                "remediation": f"按“{name}”整改；涉及方言语法时同时应用对应方言规则。",
                "confirmation_required": prefix in CONFIRM_PREFIXES or clause_id in CONFIRM_IDS,
            })
    return clauses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    clauses = parse_clauses(args.source.read_text(encoding="utf-8"))
    payload = {
        "schema_version": "2.0.0",
        "dialect": "common",
        "description": "Portable rules derived from the supplied SQL programming standard; apply with exactly one dialect catalog.",
        "rules": clauses,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(clauses)} rules to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

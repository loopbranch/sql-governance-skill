#!/usr/bin/env python3
"""Import only exhaustively audited, dialect-independent G.* clauses.

SQL-facing clauses are intentionally excluded from common.json and must be
maintained as paired MySQL/PostgreSQL rules. The allowlist is validated against
the 154-row isolation audit.
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

STATIC_IDS: set[str] = set()

COMMON_SOURCE_IDS = {
    "G.CLI.01", "G.CLI.02", "G.CLI.03", "G.CLI.04", "G.CLI.05",
    "G.CMT.01", "G.CMT.02", "G.CMT.03", "G.CMT.04", "G.CMT.05",
    "G.CMT.06", "G.CMT.07", "G.CMT.08", "G.CMT.09", "G.CMT.10",
    "G.DBS.03", "G.DBS.04", "G.DBS.06",
    "G.FMT.01", "G.FMT.02", "G.FMT.03", "G.FMT.04", "G.FMT.05",
    "G.FMT.06", "G.FMT.07", "G.FMT.08", "G.FMT.09", "G.FMT.10",
    "G.FMT.11", "G.FMT.12", "G.FMT.13",
    "G.IDX.01", "G.IDX.02", "G.IDX.03", "G.IDX.04", "G.IDX.05",
    "G.IDX.08", "G.IDX.09", "G.IDX.10",
    "G.INS.02", "G.INS.03",
    "G.KOO.01", "G.KOO.02", "G.KOO.03", "G.KOO.04", "G.KOO.05",
    "G.KOO.06", "G.KOO.07", "G.KOO.08", "G.KOO.09",
    "G.NAM.02", "G.NAM.04", "G.NAM.05", "G.NAM.06", "G.NAM.07",
    "G.NAM.08", "G.NAM.09",
    "G.SEC.01", "G.SEC.02", "G.SEC.03",
    "G.SEL.02", "G.SEL.03", "G.SEL.04", "G.SEL.06", "G.SEL.07",
    "G.SEL.09", "G.SEL.10", "G.SEL.11", "G.SEL.13", "G.SEL.14",
    "G.SEL.15", "G.SEL.16", "G.SEL.18", "G.SEL.19", "G.SEL.20",
    "G.SEL.21", "G.SEL.22", "G.SEL.23", "G.SEL.24", "G.SEL.25",
    "G.SEL.26", "G.SEL.27", "G.SEL.28", "G.SEL.29", "G.SEL.30",
    "G.SEL.31", "G.SEL.32", "G.SEL.33", "G.SEL.34",
    "G.TAB.02", "G.TAB.03", "G.TAB.06", "G.TAB.07", "G.TAB.08",
    "G.TAB.09", "G.TAB.10", "G.TAB.11", "G.TAB.12", "G.TAB.14",
    "G.TAB.17",
    "G.TXN.02", "G.TXN.03", "G.TXN.04", "G.TXN.05", "G.TXN.06",
    "G.UPD.04", "G.UPD.07",
    "G.UPG.01", "G.UPG.06", "G.UPG.09",
}

MANUAL_PREFIXES = {"DBS", "CLI", "SEC", "KOO"}
CONFIRM_PREFIXES = {"TAB", "IDX", "UPG"}
CONFIRM_IDS = {"G.DEL.02", "G.UPG.09"}
REFERENCE_IDS = {"G.FMT.08"}
RECOMMENDATION_IDS = {
    "G.FMT.02", "G.FMT.03", "G.FMT.07", "G.IDX.09", "G.IDX.10", "G.NAM.05",
}
MANDATORY_IDS = {"G.DEL.01"}

PORTABLE_OVERRIDES = {
    "G.SEC.01": "按项目的数据分类要求识别敏感字段，并通过批准的加密机制保护存储数据。",
    "G.FMT.02": "建议每行至多一条 SQL 语句，以便独立审阅和定位错误。",
    "G.FMT.03": "建议在相对独立的 SQL 程序块之间留空行。",
    "G.FMT.07": "建议使用 4 个空格缩进，避免混用制表符。",
    "G.NAM.05": "建议避免无意义的数字；允许表达版本或业务含义的数字，例如 t_order_v2。",
    "G.SEL.21": "使用 IS NULL 或 IS NOT NULL 判断空值，不能使用 = NULL 或 <> NULL。",
    "G.SEL.25": "禁止对关联或过滤字段直接套用函数或表达式；优先改写为原列上的等值或范围谓词。",
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
    "G.DEL.01": "DELETE 语句必须带能够限定目标行的 WHERE 条件。是否命中主键或索引属于执行计划评审建议，不改变缺少 WHERE 时的 Block。",
    "G.SEL.15": "统计行数使用 count(*)；只有需要忽略 NULL 时才使用 count(列名)。不得以性能理由强制用 count(1) 替代 count(*)。",
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
    "G.SEL.15": "按空值语义选择 count(*) 或 count(列名)",
}

RULE_EXAMPLES = {
    "G.FMT.02": ("每条 SELECT 各占一行", "select 1; select 2; 写在同一行"),
    "G.FMT.03": ("建表与初始化数据之间留空行", "多个独立迁移步骤连续成块，难以区分"),
    "G.FMT.07": ("子查询使用 4 个空格缩进", "同一文件混用制表符与空格缩进"),
    "G.NAM.05": ("t_order_v2 表示第二版订单模型", "t_order_73 中的 73 无业务含义"),
    "G.TAB.09": ("amount decimal(19,4) not null", "amount double precision not null"),
    "G.SEL.15": ("select count(*) from t_order", "用 select count(shipped_at) from t_order 统计总行数，漏计未发货订单"),
    "G.SEL.21": ("select id from t_order where shipped_at is null", "select id from t_order where shipped_at = null"),
    "G.SEL.25": ("where created_at >= '2026-11-21 00:00:00' and created_at < '2026-11-22 00:00:00'", "where date(created_at) = '2026-11-21'"),
    "G.DEL.01": ("delete from t_order where id = ?", "delete from t_order"),
    "G.INS.01": ("insert into t_order (id, status) values (?, ?)", "insert into t_order values (?, ?)"),
    "G.SEL.08": ("select a.id from t_a a inner join t_b b on b.id = a.id", "select a.id from t_a a full outer join t_b b on b.id = a.id"),
    "G.SEL.12": ("select id, status from t_order", "select * from t_order"),
    "G.TAB.04": ("通过应用校验关联关系，DDL 不声明外键", "constraint fk_order_user foreign key (user_id) references t_user(id)"),
    "G.TAB.16": ("create table ... (id uuid primary key, ...)", "create table ... (name varchar(64))"),
    "G.TXN.01": ("使用项目统一的默认隔离级别", "set transaction isolation level serializable"),
    "G.TXN.07": ("单库本地事务或已批准的最终一致性方案", "xa start 'order-and-stock'"),
    "G.UPD.01": ("update t_order set status = ? where id = ?", "update t_order set status = ?"),
    "G.UPD.02": ("按稳定主键范围执行 update", "update t_order set status = ? where tenant_id = ? order by id"),
    "G.UPD.03": ("按 id 范围选定批次后更新", "update t_order set status = ? where status = ? limit 1000"),
    "G.UPG.03": ("保留旧字段并采用扩展-迁移-收缩方案", "alter table t_order drop column legacy_code"),
    "G.UPG.05": ("新增目标类型字段并迁移验证", "alter table t_order alter column amount type numeric(20,2)"),
    "G.UPG.07": ("先增加可空字段并分批回填", "alter table t_order add column region_code varchar(32) not null"),
    "G.UPG.08": ("保持字段可空或采用替代表迁移方案", "alter table t_order alter column region_code set not null"),
    "G.UPG.10": ("create table if not exists t_order (...) ", "create table t_order (...)") ,
    "G.UPG.11": ("drop table if exists t_order", "drop table t_order"),
}

EVIDENCE_CONTEXT = {
    "DBS": "实例、连接与部署配置",
    "TAB": "DDL、数据模型与容量评审记录",
    "IDX": "索引 DDL、数据分布和 EXPLAIN",
    "FMT": "格式化后的 SQL 文件",
    "NAM": "schema 对象和代码标识符清单",
    "CMT": "SQL 文件头及对象注释",
    "SEL": "查询 SQL、参数和执行计划",
    "INS": "写入 SQL 与批处理设计",
    "DEL": "删除 SQL、影响行数和恢复方案",
    "UPD": "更新 SQL、稳定键和影响行数",
    "CLI": "数据库访问代码、资源生命周期和异常路径",
    "TXN": "事务边界、锁和失败恢复流程",
    "UPG": "迁移脚本、演练、备份和回滚记录",
    "SEC": "账号、传输和权限配置",
    "KOO": "版本归档、问题单和流水线产物",
}


def examples_for(clause_id: str, prefix: str, condition: str) -> dict[str, str]:
    if clause_id in RULE_EXAMPLES:
        positive, negative = RULE_EXAMPLES[clause_id]
        return {"positive": positive, "negative": negative}
    context = EVIDENCE_CONTEXT[prefix]
    return {
        "positive": f"合规证据示例：{context}能够证明“{condition}”。",
        "negative": f"不合规场景：{context}缺失，或其内容表明未满足“{condition}”。",
    }


def clean(value: str) -> str:
    value = re.sub(r"!\[[^]]*]\([^)]*\)", "", value)
    value = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>|&nbsp;", " ", value)
    # Strip Markdown delimiters, not SQL operators. In particular, `*` is
    # meaningful in SELECT * and COUNT(*) and must survive import.
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"(?<!\*)\*\*([^*]+)\*\*(?!\*)", r"\1", value)
    value = re.sub(r"(?<!_)__([^_]+)__(?!_)", r"\1", value)
    value = re.sub(r"\\([\\`*_{}\[\]()#+.!-])", r"\1", value)
    value = re.sub(r"\s+", " ", value).strip(" #:-")
    return value


def level_for(clause_id: str, text: str) -> str:
    if clause_id in REFERENCE_IDS:
        return "reference"
    if clause_id in RECOMMENDATION_IDS:
        return "recommendation"
    if clause_id in MANDATORY_IDS:
        return "mandatory"
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
            if re.match(r"^#{1,4}\s", line):
                break
            stripped = clean(line)
            if not stripped or line.lstrip().startswith(("|", "```", "* ", "- ")):
                continue
            prose.append(stripped)
            if sum(map(len, prose)) >= 420:
                break
        for clause_id in expand_id(match.group(2)):
            if clause_id not in COMMON_SOURCE_IDS:
                continue
            prefix = clause_id.split(".")[1]
            name = NAME_OVERRIDES.get(clause_id) or title or clause_id
            # Severity follows the complete source clause, not the portable display name.
            level = level_for(clause_id, " ".join([title, *prose]) or name)
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
                "examples": examples_for(clause_id, prefix, condition),
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
        "description": "Shared SQL governance policies; apply with exactly one dialect catalog.",
        "rules": clauses,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(clauses)} rules to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

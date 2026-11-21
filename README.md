# SQL Governance Skill

面向多仓库复用的 MySQL/PostgreSQL 编程规范 SKILL。独立 GitHub 仓库是规则唯一事实来源；业务主工程以 git submodule 锁定精确 commit，实现统一维护、显式升级和可审计回退。

## 仓库结构

```text
sql-governance-skill/
├── SKILL.md                         # 自动触发、两场景流程、分层与确认机制
├── agents/openai.yaml               # SKILL 展示元数据
├── rules/
│   ├── catalog.json                 # 方言路由和加载顺序
│   ├── common.json                  # 154 条原文条款的公共抽象
│   ├── mysql.json                   # MySQL 专属实现与语法
│   ├── postgresql.json              # PostgreSQL 专属实现与语法
│   ├── schema.json                  # 规则 JSON Schema
│   └── README.md                    # 字段、维护和版本约定
├── templates/
│   ├── design-review.md             # 方案期意见模板
│   ├── gate-report.md               # CodeCheck/提交/PR 门禁报告
│   └── developer-confirmation.md    # 高风险变更明确确认模板
├── references/
│   ├── severity-model.md            # 层级、门禁和静态/人工判定模型
│   ├── source-mapping.md            # 原规范映射原则与公开边界
│   └── submodule-integration.md      # 引入、克隆、升级、锁定与一致性
├── scripts/
│   ├── validate_rules.py            # 无第三方依赖的规则结构校验
│   ├── import_standard.py            # 从编号 Markdown 规范重建公共追溯目录
│   └── sql_guard.py                 # MySQL/PostgreSQL 高置信静态 Block 门禁
├── tests/test_sql_guard.py           # 双方言与绕过场景回归测试
├── CHANGELOG.md                     # 版本变更记录
└── VERSION                           # 当前发布版本
```

SKILL 逻辑与结构化规则分离：代理入口只定义何时触发和如何执行，具体条款由 `rules/catalog.json` 提供。其他团队可以只消费规则 JSON，也可以整体作为 SKILL 使用。

## 快速验证

```bash
python3 scripts/validate_rules.py
python3 scripts/sql_guard.py --dialect mysql path/to/mysql-change.sql
python3 scripts/sql_guard.py --dialect postgresql path/to/postgresql-change.sql
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

`sql_guard.py` 对已实现的高置信禁止项返回退出码 `1`，输入、读取或方言不明确返回 `2`，通过返回 `0`；支持 `--format json`，并通过 `checked_rules` 明确本次自动覆盖范围。`--dialect auto` 只在证据单一时推断，无法确定时阻断结论。脚本通过不代表 170 条规则全部通过，人工和混合规则仍按 `SKILL.md` 检视。

## 主工程引入

```bash
git submodule add https://github.com/loopbranch/sql-governance-skill.git .skills/sql-governance
git clone --recurse-submodules <main-repo-url>
# 对已克隆工程：
git submodule update --init --recursive
```

升级、锁定、评审和多仓库一致性流程见 [references/submodule-integration.md](references/submodule-integration.md)。核心原则是：`update --remote` 用于获取候选更新，主工程 commit 中的 gitlink 才是最终锁定版本；禁止运行时自动漂移。

## 公共发布前检查

- 确认附件内容及衍生规则的公开授权，移除内网链接、个人数据和敏感信息；
- 配置分支保护：规则变更必须 PR、至少一名规则所有者审批、状态检查通过；
- 创建 `CODEOWNERS`（按组织账号填写）并启用签名 tag；
- 本次破坏性升级在合并后发布 `v2.0.0`，发布说明引用 `CHANGELOG.md`。

## 设计边界

- 本仓库不执行生产 SQL，也不代替数据库变更审批系统。
- 开发者“确认”只允许继续处理准确描述的方案，不豁免 Block，不等于批准生产执行。
- `common.json` 覆盖附件全部 154 个编号条款；MySQL/PostgreSQL 差异规则单独维护。静态脚本通过不等于完整合规，manual/hybrid 条款仍需报告证据。

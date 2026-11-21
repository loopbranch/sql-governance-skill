# Changelog

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 预留后续规则与检测器变更。

## [2.0.0] - 2026-11-21

### Added

- 附件 154 个编号条款的完整公共追溯目录。
- MySQL 与 PostgreSQL 独立差异规则，覆盖编码、排序规则、表实现、时间、长文本索引、主键、在线索引、分区和批处理。
- 静态门禁 `--dialect mysql|postgresql|auto`，方言不明确时阻断方言结论。
- 标准 Markdown 条款导入工具和跨文件目录校验。

### Changed

- 规则目录改为 `common.json` 加一个方言文件的加载模型。
- 修复字符串内 `where`、CTE `select *`、字段类型修改及新增 NOT NULL 字段等漏检。
- 这是门禁语义破坏性升级，消费方必须通过显式 submodule PR 升级。

### Fixed

- SQL 门禁只按顶层主语句识别 DML，避免 `FOR UPDATE`、列属性和 CTE 子查询误报。
- 覆盖 PostgreSQL `FULL OUTER JOIN`、`ALTER COLUMN`、表级 serial/identity 主键、临时表和 CTE INSERT。
- 按方言处理 `#`，检查所有 MySQL 字符集声明，并将 PostgreSQL 并发索引保留为上下文相关的 hybrid 规则。
- 公共规则严重级别读取完整条款，正反例改为可执行 SQL 或具体证据场景；`static` 与脚本实际覆盖保持一致。
- 修复 Markdown 导入器删除 `select *`、`count(*)` 中星号的问题，并增加语义快照测试。
- lexer 按 MySQL 5.7 与 PostgreSQL 16 分别处理 `--`、反斜杠字符串、`#` 和嵌套块注释。
- 递归检查 PostgreSQL data-modifying CTE，补齐 UUID 主键类型、弱方言线索和方言 static 清单门禁。
- 将 34 个存在差异的源条款从公共目录移出并成对拆为 MySQL/PostgreSQL 规则；每个加载路径仍完整覆盖 154 个源条款。

## [1.0.0] - 2026-11-21

### Added

- 首版 SQL Governance SKILL，覆盖方案期与代码门禁两个触发场景。
- 四层规范模型与 Block/Warn/Info 门禁映射。
- 结构性变更和大批量数据变更的显式开发者确认机制。
- 24 条机器可读示例规则，覆盖命名、格式、建表、字段、索引、DML、事务、性能、升级、安全和归档。
- 方案期意见、门禁检视和开发者确认模板。
- git submodule 引入、克隆、升级、锁定、回退及多仓库一致性说明。
- 规则目录校验脚本，以及可对高置信 Block 返回非零退出码的静态 SQL 门禁脚本；均无第三方依赖。

[Unreleased]: https://github.com/loopbranch/sql-governance-skill/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/loopbranch/sql-governance-skill/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/loopbranch/sql-governance-skill/releases/tag/v1.0.0

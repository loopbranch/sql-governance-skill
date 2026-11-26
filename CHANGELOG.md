# Changelog

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added

- 禁止通过 `TRUNCATE` 清除表数据。MySQL 与 PostgreSQL 的静态门禁新增阻断规则，属于 MAJOR 变更。

- PostgreSQL 归档 SQL 新增 `--archived-sql` 静态阻断无保护的新增列。归档门禁通过 `--archive-replay-evidence` 强制校验整批 SQL 同库重跑和结构及数据快照，缺证据、失败或快照不一致均阻断。新增 Block 属于 MAJOR 变更。

- 支持按批次读取可信迁移往返回执，对已经验证且定位明确的回滚逆操作单独判定。

### Changed

- MySQL 和 PostgreSQL 的服务隔离规则明确由部署或连接配置提供数据库、账号、schema 和搜索路径，并更新示例。
- 新增归档 SQL 人工 Block 门禁，禁止在文件内指定目标环境。新增阻断条件属于 MAJOR 变更。

### Fixed

- 澄清归档重跑证据要求。升级和回滚各自在同一个目标库连续执行至少两次是门禁必需项，多环境验证按兼容需求单独执行。
- 支持 PostgreSQL UTF-8 裸标识符中的组合字符，保留主键列名的非 ASCII 大小写和 Unicode 写法差异。
- PostgreSQL 的列名、类型及表达式中的 `engine`、`charset` 和 `auto_increment` 可以通过同名 MySQL 表语法筛查。
- PostgreSQL 模式发现 MySQL 表选项、列属性、MySQL 特有的 `ALTER TABLE` 子句或反引号标识符时输出 `POSTGRESQL-TAB-001` Warn，提示复核数据库兼容性。
- PostgreSQL 自增门禁按实际主键约束关联列，普通同名列、非主键自增列和带引号的约束名称可以通过。

## [2.0.0] - 2026-11-21

### Added

- 附件 154 个编号条款的完整可追溯目录。
- MySQL 与 PostgreSQL 独立差异规则，覆盖编码、排序规则、表实现、时间、长文本索引、主键、在线索引、分区和批处理。
- 静态门禁 `--dialect mysql|postgresql|auto`，方言不明确时阻断方言结论。
- 标准 Markdown 条款导入工具和跨文件目录校验。

### Changed

- 规则目录改为 `common.json` 加一个方言文件的加载模型。
- 修复字符串内 `where`、CTE `select *`、字段类型修改及新增 NOT NULL 字段等漏检。
- 这是门禁语义破坏性升级，消费方必须通过显式 submodule PR 升级。

### Fixed

- SQL 门禁只按顶层主语句识别 DML，避免 `FOR UPDATE`、列属性和 CTE 子查询误报。
- 覆盖 PostgreSQL `ALTER COLUMN`、表级 serial/identity 主键、临时表和 CTE INSERT。
- 按方言处理 `#`，检查所有 MySQL 字符集声明，并将 PostgreSQL 并发索引保留为上下文相关的 hybrid 规则。
- 公共规则严重级别读取完整条款，正反例改为可执行 SQL 或具体证据场景；`static` 与脚本实际覆盖保持一致。
- 修复 Markdown 导入器删除 `select *`、`count(*)` 中星号的问题，并增加语义快照测试。
- lexer 按 MySQL 5.7 与 PostgreSQL 16 分别处理 `--`、反斜杠字符串、`#` 和嵌套块注释。
- 递归检查 PostgreSQL data-modifying CTE，将 UUID 存储候选交由模型与写入路径复核，按类型声明位置识别方言，并校验静态门禁清单。
- 将 86 条重复政策归入公共层。每个方言加载路径包含 110 条共同政策及对应的 44 个方言源条款。
- PostgreSQL 允许 FULL OUTER JOIN 和 CROSS JOIN LATERAL。MySQL 检查省略 COLUMN 的删列语句，支持显式指定 NO_BACKSLASH_ESCAPES。
- 分离 DELETE 的 WHERE 门禁和索引建议。字符集、引擎、分布式事务的候选命中提示复核，命名中的数字及指定排版规则降为 Warn。
- 自动 finding 全部改用方言规则 ID，并增加跨方言 ID 泄漏、成对覆盖和 154 条审计表完整性测试。

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

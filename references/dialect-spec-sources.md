# 方言规范依据

规则以 PostgreSQL 16 与 MySQL 5.7 的官方语言文档为语法、类型和行为事实来源。项目治理策略可以比数据库语法更严格，但不得把“项目禁止”写成“数据库不支持”，也不得用一方言的语法解释另一方言。

## PostgreSQL 16

- [词法结构、字符串、标识符与注释](https://www.postgresql.org/docs/16/sql-syntax-lexical.html)：普通字符串、`E''`、双引号标识符、63 字节标识符、可嵌套块注释。
- [Schema](https://www.postgresql.org/docs/16/ddl-schemas.html)：database 内 schema、`search_path` 与权限边界。
- [数据类型](https://www.postgresql.org/docs/16/datatype.html)与 [uuid](https://www.postgresql.org/docs/16/datatype-uuid.html)：类型、原生 UUID 存储。
- [COMMENT](https://www.postgresql.org/docs/16/sql-comment.html)：`COMMENT ON` 语法。
- [SELECT](https://www.postgresql.org/docs/16/sql-select.html)、[UPDATE](https://www.postgresql.org/docs/16/sql-update.html)、[DELETE](https://www.postgresql.org/docs/16/sql-delete.html)：各语句真实 grammar。
- [WITH](https://www.postgresql.org/docs/16/queries-with.html)：data-modifying CTE 的 `INSERT`/`UPDATE`/`DELETE` 行为。
- [系统列](https://www.postgresql.org/docs/16/ddl-system-columns.html)：`ctid` 不能作为长期行标识。
- [ALTER TABLE](https://www.postgresql.org/docs/16/sql-altertable.html)：字段类型与约束变更语法。
- [显式锁](https://www.postgresql.org/docs/16/explicit-locking.html)与 [PREPARE TRANSACTION](https://www.postgresql.org/docs/16/sql-prepare-transaction.html)：锁模式和两阶段提交。
- [并发索引](https://www.postgresql.org/docs/16/sql-createindex.html#SQL-CREATEINDEX-CONCURRENTLY)：`CONCURRENTLY` 的限制与失败状态。

## MySQL 5.7

- [注释](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/comments.html)：`#`、`--` 后继空白要求、非嵌套块注释和 executable comments。
- [字符串](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/string-literals.html)：默认反斜杠转义、`NO_BACKSLASH_ESCAPES` 与 `ANSI_QUOTES`。
- [标识符长度](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/identifier-length.html)：多数对象 64 字符及对象类别差异。
- [字符集与排序规则](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/charset.html)及 [InnoDB](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/innodb-storage-engine.html)：`utf8mb4`、collation 与表引擎。
- [JOIN](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/join.html)：`JOIN`/`CROSS JOIN`/`INNER JOIN` 关系及 5.7 支持范围。
- [UPDATE](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/update.html)与 [DELETE](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/delete.html)：单表 `ORDER BY`/`LIMIT`、多表语法与赋值顺序。
- [ALTER TABLE](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/alter-table.html)：`MODIFY`/`CHANGE`、在线 DDL 和列属性重述。
- [XA](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/xa.html)与 [InnoDB locking](https://docs.oracle.com/cd/E17952_01/mysql-5.7-en/innodb-locking.html)：分布式事务、record/gap/next-key locks。

## 维护要求

1. `common.json` 只保存两种方言在判定条件、语法和整改方式上均无差异的规则。
2. 任一差异条款必须从公共文件移出，并在 `mysql.json`、`postgresql.json` 各保留一条 `source` 追溯规则。
3. `validate_rules.py` 验证每个加载路径都恰好覆盖 154 个源条款，并禁止拆分条款同时残留于公共文件。
4. 升级数据库基线版本时，先复核以上官方章节，再修改规则与黑盒测试。

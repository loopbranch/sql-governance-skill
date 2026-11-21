# 154 条规则方言隔离审计

审计基线：MySQL 5.7、PostgreSQL 16。`common` 只保留与数据库语法、对象、类型、优化器、驱动、事务、安全配置和 DDL/DML 行为均无关的纯组织/文本/归档规则。

表中所有“拆分”结论均以 [MySQL 5.7 / PostgreSQL 16 官方规范入口](dialect-spec-sources.md)为事实依据；最后一列标明该条实际需要核对的规范主题。项目治理要求可以比语言能力更严格，但规则文本必须明确区分治理禁止与数据库不支持。

| 源条款 | 结论 | MySQL 规则 | PostgreSQL 规则 | 保留/拆分依据 |
|---|---|---|---|---|
| `G.DBS.01` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.02` | 拆分 | `MYSQL-DBS-002` | `POSTGRESQL-DBS-002` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.03` | 拆分 | `MYSQL-GDBS-003` | `POSTGRESQL-GDBS-003` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.04` | 保留 common | `经 common 加载：G.DBS.04` | `经 common 加载：G.DBS.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.DBS.05` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.06` | 拆分 | `MYSQL-GDBS-006` | `POSTGRESQL-GDBS-006` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.TAB.01` | 拆分 | `MYSQL-TAB-001` | `POSTGRESQL-TAB-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.02` | 保留 common | `经 common 加载：G.TAB.02` | `经 common 加载：G.TAB.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.TAB.03` | 拆分 | `MYSQL-GTAB-003` | `POSTGRESQL-GTAB-003` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.04` | 拆分 | `MYSQL-GTAB-004` | `POSTGRESQL-GTAB-004` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.05` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.06` | 拆分 | `MYSQL-GTAB-006` | `POSTGRESQL-GTAB-006` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.07` | 拆分 | `MYSQL-GTAB-007` | `POSTGRESQL-GTAB-007` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.08` | 拆分 | `MYSQL-GTAB-008` | `POSTGRESQL-GTAB-008` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.09` | 拆分 | `MYSQL-GTAB-009` | `POSTGRESQL-GTAB-009` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.10` | 拆分 | `MYSQL-GTAB-010` | `POSTGRESQL-GTAB-010` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.11` | 拆分 | `MYSQL-GTAB-011` | `POSTGRESQL-GTAB-011` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.12` | 拆分 | `MYSQL-GTAB-012` | `POSTGRESQL-GTAB-012` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.13` | 拆分 | `MYSQL-TAB-013` | `POSTGRESQL-TAB-013` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.14` | 拆分 | `MYSQL-GTAB-014` | `POSTGRESQL-GTAB-014` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.15` | 拆分 | `MYSQL-TIME-001` | `POSTGRESQL-TIME-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.16` | 拆分 | `MYSQL-GTAB-016` | `POSTGRESQL-GTAB-016` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.17` | 拆分 | `MYSQL-GTAB-017` | `POSTGRESQL-GTAB-017` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.18` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.19` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.IDX.01` | 拆分 | `MYSQL-GIDX-001` | `POSTGRESQL-GIDX-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.02` | 拆分 | `MYSQL-GIDX-002` | `POSTGRESQL-GIDX-002` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.03` | 拆分 | `MYSQL-GIDX-003` | `POSTGRESQL-GIDX-003` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.04` | 拆分 | `MYSQL-GIDX-004` | `POSTGRESQL-GIDX-004` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.05` | 拆分 | `MYSQL-GIDX-005` | `POSTGRESQL-GIDX-005` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.06` | 拆分 | `MYSQL-IDX-001` | `POSTGRESQL-IDX-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.07` | 拆分 | `MYSQL-IDX-001` | `POSTGRESQL-IDX-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.08` | 拆分 | `MYSQL-GIDX-008` | `POSTGRESQL-GIDX-008` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.09` | 拆分 | `MYSQL-GIDX-009` | `POSTGRESQL-GIDX-009` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.10` | 拆分 | `MYSQL-GIDX-010` | `POSTGRESQL-GIDX-010` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.11` | 拆分 | `MYSQL-PK-001` | `POSTGRESQL-PK-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.FMT.01` | 拆分 | `MYSQL-GFMT-001` | `POSTGRESQL-GFMT-001` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.02` | 保留 common | `经 common 加载：G.FMT.02` | `经 common 加载：G.FMT.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.03` | 保留 common | `经 common 加载：G.FMT.03` | `经 common 加载：G.FMT.03` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.04` | 拆分 | `MYSQL-GFMT-004` | `POSTGRESQL-GFMT-004` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.05` | 拆分 | `MYSQL-GFMT-005` | `POSTGRESQL-GFMT-005` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.06` | 拆分 | `MYSQL-GFMT-006` | `POSTGRESQL-GFMT-006` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.07` | 保留 common | `经 common 加载：G.FMT.07` | `经 common 加载：G.FMT.07` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.08` | 拆分 | `MYSQL-GFMT-008` | `POSTGRESQL-GFMT-008` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.09` | 拆分 | `MYSQL-GFMT-009` | `POSTGRESQL-GFMT-009` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.10` | 拆分 | `MYSQL-GFMT-010` | `POSTGRESQL-GFMT-010` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.11` | 拆分 | `MYSQL-GFMT-011` | `POSTGRESQL-GFMT-011` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.FMT.12` | 保留 common | `经 common 加载：G.FMT.12` | `经 common 加载：G.FMT.12` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.13` | 拆分 | `MYSQL-GFMT-013` | `POSTGRESQL-GFMT-013` | 底层边界涉及 lexical/stored-program grammar；按双方言官方规范分别判定。 |
| `G.NAM.01` | 拆分 | `MYSQL-NAM-001` | `POSTGRESQL-NAM-001` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.02` | 拆分 | `MYSQL-GNAM-002` | `POSTGRESQL-GNAM-002` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.03` | 拆分 | `MYSQL-NAM-003` | `POSTGRESQL-NAM-003` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.04` | 保留 common | `经 common 加载：G.NAM.04` | `经 common 加载：G.NAM.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.05` | 保留 common | `经 common 加载：G.NAM.05` | `经 common 加载：G.NAM.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.06` | 保留 common | `经 common 加载：G.NAM.06` | `经 common 加载：G.NAM.06` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.07` | 拆分 | `MYSQL-GNAM-007` | `POSTGRESQL-GNAM-007` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.08` | 拆分 | `MYSQL-GNAM-008` | `POSTGRESQL-GNAM-008` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.09` | 拆分 | `MYSQL-GNAM-009` | `POSTGRESQL-GNAM-009` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.CMT.01` | 保留 common | `经 common 加载：G.CMT.01` | `经 common 加载：G.CMT.01` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.02` | 保留 common | `经 common 加载：G.CMT.02` | `经 common 加载：G.CMT.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.03` | 拆分 | `MYSQL-GCMT-003` | `POSTGRESQL-GCMT-003` | 底层边界涉及 comments/encoding；按双方言官方规范分别判定。 |
| `G.CMT.04` | 保留 common | `经 common 加载：G.CMT.04` | `经 common 加载：G.CMT.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.05` | 保留 common | `经 common 加载：G.CMT.05` | `经 common 加载：G.CMT.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.06` | 拆分 | `MYSQL-GCMT-006` | `POSTGRESQL-GCMT-006` | 底层边界涉及 comments/encoding；按双方言官方规范分别判定。 |
| `G.CMT.07` | 拆分 | `MYSQL-GCMT-007` | `POSTGRESQL-GCMT-007` | 底层边界涉及 comments/encoding；按双方言官方规范分别判定。 |
| `G.CMT.08` | 保留 common | `经 common 加载：G.CMT.08` | `经 common 加载：G.CMT.08` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.09` | 保留 common | `经 common 加载：G.CMT.09` | `经 common 加载：G.CMT.09` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.10` | 保留 common | `经 common 加载：G.CMT.10` | `经 common 加载：G.CMT.10` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.SEL.01` | 拆分 | `MYSQL-SEL-001` | `POSTGRESQL-SEL-001` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.02` | 拆分 | `MYSQL-GSEL-002` | `POSTGRESQL-GSEL-002` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.03` | 拆分 | `MYSQL-GSEL-003` | `POSTGRESQL-GSEL-003` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.04` | 拆分 | `MYSQL-GSEL-004` | `POSTGRESQL-GSEL-004` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.05` | 拆分 | `MYSQL-SEL-005` | `POSTGRESQL-SEL-005` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.06` | 拆分 | `MYSQL-GSEL-006` | `POSTGRESQL-GSEL-006` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.07` | 拆分 | `MYSQL-GSEL-007` | `POSTGRESQL-GSEL-007` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.08` | 拆分 | `MYSQL-SEL-008` | `POSTGRESQL-SEL-008` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.09` | 拆分 | `MYSQL-GSEL-009` | `POSTGRESQL-GSEL-009` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.10` | 拆分 | `MYSQL-GSEL-010` | `POSTGRESQL-GSEL-010` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.11` | 拆分 | `MYSQL-GSEL-011` | `POSTGRESQL-GSEL-011` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.12` | 拆分 | `MYSQL-GSEL-012` | `POSTGRESQL-GSEL-012` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.13` | 拆分 | `MYSQL-GSEL-013` | `POSTGRESQL-GSEL-013` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.14` | 拆分 | `MYSQL-GSEL-014` | `POSTGRESQL-GSEL-014` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.15` | 拆分 | `MYSQL-GSEL-015` | `POSTGRESQL-GSEL-015` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.16` | 拆分 | `MYSQL-GSEL-016` | `POSTGRESQL-GSEL-016` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.17` | 拆分 | `MYSQL-SEL-017` | `POSTGRESQL-SEL-017` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.18` | 拆分 | `MYSQL-GSEL-018` | `POSTGRESQL-GSEL-018` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.19` | 拆分 | `MYSQL-GSEL-019` | `POSTGRESQL-GSEL-019` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.20` | 拆分 | `MYSQL-GSEL-020` | `POSTGRESQL-GSEL-020` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.21` | 拆分 | `MYSQL-GSEL-021` | `POSTGRESQL-GSEL-021` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.22` | 拆分 | `MYSQL-GSEL-022` | `POSTGRESQL-GSEL-022` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.23` | 拆分 | `MYSQL-GSEL-023` | `POSTGRESQL-GSEL-023` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.24` | 拆分 | `MYSQL-GSEL-024` | `POSTGRESQL-GSEL-024` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.25` | 拆分 | `MYSQL-GSEL-025` | `POSTGRESQL-GSEL-025` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.26` | 拆分 | `MYSQL-GSEL-026` | `POSTGRESQL-GSEL-026` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.27` | 拆分 | `MYSQL-GSEL-027` | `POSTGRESQL-GSEL-027` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.28` | 拆分 | `MYSQL-GSEL-028` | `POSTGRESQL-GSEL-028` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.29` | 拆分 | `MYSQL-GSEL-029` | `POSTGRESQL-GSEL-029` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.30` | 拆分 | `MYSQL-GSEL-030` | `POSTGRESQL-GSEL-030` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.31` | 拆分 | `MYSQL-GSEL-031` | `POSTGRESQL-GSEL-031` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.32` | 拆分 | `MYSQL-GSEL-032` | `POSTGRESQL-GSEL-032` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.33` | 拆分 | `MYSQL-GSEL-033` | `POSTGRESQL-GSEL-033` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.34` | 拆分 | `MYSQL-GSEL-034` | `POSTGRESQL-GSEL-034` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.35` | 拆分 | `MYSQL-SEL-035` | `POSTGRESQL-SEL-035` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.INS.01` | 拆分 | `MYSQL-GINS-001` | `POSTGRESQL-GINS-001` | 底层边界涉及 INSERT/coercion；按双方言官方规范分别判定。 |
| `G.INS.02` | 拆分 | `MYSQL-GINS-002` | `POSTGRESQL-GINS-002` | 底层边界涉及 INSERT/coercion；按双方言官方规范分别判定。 |
| `G.INS.03` | 拆分 | `MYSQL-GINS-003` | `POSTGRESQL-GINS-003` | 底层边界涉及 INSERT/coercion；按双方言官方规范分别判定。 |
| `G.DEL.01` | 拆分 | `MYSQL-GDEL-001` | `POSTGRESQL-GDEL-001` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.DEL.02` | 拆分 | `MYSQL-UPD-001` | `POSTGRESQL-UPD-001` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.DEL.03` | 拆分 | `MYSQL-DEL-003` | `POSTGRESQL-DEL-003` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.UPD.01` | 拆分 | `MYSQL-GUPD-001` | `POSTGRESQL-GUPD-001` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.02` | 拆分 | `MYSQL-UPD-002` | `POSTGRESQL-UPD-002` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.03` | 拆分 | `MYSQL-UPD-001` | `POSTGRESQL-UPD-001` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.04` | 拆分 | `MYSQL-GUPD-004` | `POSTGRESQL-GUPD-004` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.05` | 拆分 | `MYSQL-UPD-005` | `POSTGRESQL-UPD-005` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.06` | 拆分 | `MYSQL-UPD-006` | `POSTGRESQL-UPD-006` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.07` | 拆分 | `MYSQL-GUPD-007` | `POSTGRESQL-GUPD-007` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.CLI.01` | 拆分 | `MYSQL-GCLI-001` | `POSTGRESQL-GCLI-001` | 底层边界涉及 prepared statements/connections；按双方言官方规范分别判定。 |
| `G.CLI.02` | 拆分 | `MYSQL-GCLI-002` | `POSTGRESQL-GCLI-002` | 底层边界涉及 prepared statements/connections；按双方言官方规范分别判定。 |
| `G.CLI.03` | 拆分 | `MYSQL-GCLI-003` | `POSTGRESQL-GCLI-003` | 底层边界涉及 prepared statements/connections；按双方言官方规范分别判定。 |
| `G.CLI.04` | 拆分 | `MYSQL-GCLI-004` | `POSTGRESQL-GCLI-004` | 底层边界涉及 prepared statements/connections；按双方言官方规范分别判定。 |
| `G.CLI.05` | 拆分 | `MYSQL-GCLI-005` | `POSTGRESQL-GCLI-005` | 底层边界涉及 prepared statements/connections；按双方言官方规范分别判定。 |
| `G.TXN.01` | 拆分 | `MYSQL-GTXN-001` | `POSTGRESQL-GTXN-001` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.02` | 拆分 | `MYSQL-GTXN-002` | `POSTGRESQL-GTXN-002` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.03` | 拆分 | `MYSQL-GTXN-003` | `POSTGRESQL-GTXN-003` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.04` | 拆分 | `MYSQL-GTXN-004` | `POSTGRESQL-GTXN-004` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.05` | 拆分 | `MYSQL-GTXN-005` | `POSTGRESQL-GTXN-005` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.06` | 拆分 | `MYSQL-GTXN-006` | `POSTGRESQL-GTXN-006` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.07` | 拆分 | `MYSQL-TXN-007` | `POSTGRESQL-TXN-007` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.08` | 拆分 | `MYSQL-TXN-008` | `POSTGRESQL-TXN-008` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.UPG.01` | 拆分 | `MYSQL-GUPG-001` | `POSTGRESQL-GUPG-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.02` | 拆分 | `MYSQL-UPG-002` | `POSTGRESQL-UPG-002` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.03` | 拆分 | `MYSQL-GUPG-003` | `POSTGRESQL-GUPG-003` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.04` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.05` | 拆分 | `MYSQL-UPG-005` | `POSTGRESQL-UPG-005` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.06` | 拆分 | `MYSQL-GUPG-006` | `POSTGRESQL-GUPG-006` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.07` | 拆分 | `MYSQL-UPG-007` | `POSTGRESQL-UPG-007` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.08` | 拆分 | `MYSQL-UPG-008` | `POSTGRESQL-UPG-008` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.09` | 拆分 | `MYSQL-GUPG-009` | `POSTGRESQL-GUPG-009` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.10` | 拆分 | `MYSQL-GUPG-010` | `POSTGRESQL-GUPG-010` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.11` | 拆分 | `MYSQL-GUPG-011` | `POSTGRESQL-GUPG-011` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.12` | 拆分 | `MYSQL-DDL-001` | `POSTGRESQL-DDL-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.13` | 拆分 | `MYSQL-DDL-001` | `POSTGRESQL-DDL-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.SEC.01` | 拆分 | `MYSQL-GSEC-001` | `POSTGRESQL-GSEC-001` | 底层边界涉及 TLS/accounts/encryption；按双方言官方规范分别判定。 |
| `G.SEC.02` | 拆分 | `MYSQL-GSEC-002` | `POSTGRESQL-GSEC-002` | 底层边界涉及 TLS/accounts/encryption；按双方言官方规范分别判定。 |
| `G.SEC.03` | 拆分 | `MYSQL-GSEC-003` | `POSTGRESQL-GSEC-003` | 底层边界涉及 TLS/accounts/encryption；按双方言官方规范分别判定。 |
| `G.KOO.01` | 保留 common | `经 common 加载：G.KOO.01` | `经 common 加载：G.KOO.01` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.02` | 保留 common | `经 common 加载：G.KOO.02` | `经 common 加载：G.KOO.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.03` | 保留 common | `经 common 加载：G.KOO.03` | `经 common 加载：G.KOO.03` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.04` | 保留 common | `经 common 加载：G.KOO.04` | `经 common 加载：G.KOO.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.05` | 保留 common | `经 common 加载：G.KOO.05` | `经 common 加载：G.KOO.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.06` | 拆分 | `MYSQL-GKOO-006` | `POSTGRESQL-GKOO-006` | 底层边界涉及 release/process governance；按双方言官方规范分别判定。 |
| `G.KOO.07` | 保留 common | `经 common 加载：G.KOO.07` | `经 common 加载：G.KOO.07` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.08` | 保留 common | `经 common 加载：G.KOO.08` | `经 common 加载：G.KOO.08` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.09` | 保留 common | `经 common 加载：G.KOO.09` | `经 common 加载：G.KOO.09` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |

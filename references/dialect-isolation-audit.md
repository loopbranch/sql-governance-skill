# 154 条规则方言隔离审计

审计基线：MySQL 5.7、PostgreSQL 16。`common` 保留双方言的判定条件和整改方式相同的政策；版本、语法或实际检查路径不同的规则放在各自的方言目录。

表中所有“拆分”结论均以 [MySQL 5.7 / PostgreSQL 16 官方规范入口](dialect-spec-sources.md)为事实依据；最后一列标明该条实际需要核对的规范主题。项目治理要求可以比语言能力更严格，但规则文本必须明确区分治理禁止与数据库不支持。

| 源条款 | 结论 | MySQL 规则 | PostgreSQL 规则 | 保留/拆分依据 |
|---|---|---|---|---|
| `G.DBS.01` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.02` | 拆分 | `MYSQL-DBS-002` | `POSTGRESQL-DBS-002` | 部署按方言配置独立数据库或 schema、账号权限及对象解析上下文。归档 SQL 适用对应的 DBS-003。 |
| `G.DBS.03` | 保留 common | `经 common 加载：G.DBS.03` | `经 common 加载：G.DBS.03` | 两端使用相同的治理条件和整改原则。 |
| `G.DBS.04` | 保留 common | `经 common 加载：G.DBS.04` | `经 common 加载：G.DBS.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.DBS.05` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 schema/encoding/privileges；按双方言官方规范分别判定。 |
| `G.DBS.06` | 保留 common | `经 common 加载：G.DBS.06` | `经 common 加载：G.DBS.06` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.01` | 拆分 | `MYSQL-TAB-001` | `POSTGRESQL-TAB-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.02` | 保留 common | `经 common 加载：G.TAB.02` | `经 common 加载：G.TAB.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.TAB.03` | 保留 common | `经 common 加载：G.TAB.03` | `经 common 加载：G.TAB.03` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.04` | 拆分 | `MYSQL-GTAB-004` | `POSTGRESQL-GTAB-004` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.05` | 拆分 | `MYSQL-ENC-001` | `POSTGRESQL-ENC-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.06` | 保留 common | `经 common 加载：G.TAB.06` | `经 common 加载：G.TAB.06` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.07` | 保留 common | `经 common 加载：G.TAB.07` | `经 common 加载：G.TAB.07` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.08` | 保留 common | `经 common 加载：G.TAB.08` | `经 common 加载：G.TAB.08` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.09` | 保留 common | `经 common 加载：G.TAB.09` | `经 common 加载：G.TAB.09` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.10` | 保留 common | `经 common 加载：G.TAB.10` | `经 common 加载：G.TAB.10` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.11` | 保留 common | `经 common 加载：G.TAB.11` | `经 common 加载：G.TAB.11` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.12` | 保留 common | `经 common 加载：G.TAB.12` | `经 common 加载：G.TAB.12` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.13` | 拆分 | `MYSQL-TAB-013` | `POSTGRESQL-TAB-013` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.14` | 保留 common | `经 common 加载：G.TAB.14` | `经 common 加载：G.TAB.14` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.15` | 拆分 | `MYSQL-TIME-001` | `POSTGRESQL-TIME-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.16` | 拆分 | `MYSQL-GTAB-016` | `POSTGRESQL-GTAB-016` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.17` | 保留 common | `经 common 加载：G.TAB.17` | `经 common 加载：G.TAB.17` | 两端使用相同的治理条件和整改原则。 |
| `G.TAB.18` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.TAB.19` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 types/DDL/constraints/partitioning；按双方言官方规范分别判定。 |
| `G.IDX.01` | 保留 common | `经 common 加载：G.IDX.01` | `经 common 加载：G.IDX.01` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.02` | 保留 common | `经 common 加载：G.IDX.02` | `经 common 加载：G.IDX.02` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.03` | 保留 common | `经 common 加载：G.IDX.03` | `经 common 加载：G.IDX.03` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.04` | 保留 common | `经 common 加载：G.IDX.04` | `经 common 加载：G.IDX.04` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.05` | 保留 common | `经 common 加载：G.IDX.05` | `经 common 加载：G.IDX.05` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.06` | 拆分 | `MYSQL-IDX-001` | `POSTGRESQL-IDX-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.07` | 拆分 | `MYSQL-IDX-001` | `POSTGRESQL-IDX-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.IDX.08` | 保留 common | `经 common 加载：G.IDX.08` | `经 common 加载：G.IDX.08` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.09` | 保留 common | `经 common 加载：G.IDX.09` | `经 common 加载：G.IDX.09` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.10` | 保留 common | `经 common 加载：G.IDX.10` | `经 common 加载：G.IDX.10` | 两端使用相同的治理条件和整改原则。 |
| `G.IDX.11` | 拆分 | `MYSQL-PK-001` | `POSTGRESQL-PK-001` | 底层边界涉及 indexes/optimizer；按双方言官方规范分别判定。 |
| `G.FMT.01` | 保留 common | `经 common 加载：G.FMT.01` | `经 common 加载：G.FMT.01` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.02` | 保留 common | `经 common 加载：G.FMT.02` | `经 common 加载：G.FMT.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.03` | 保留 common | `经 common 加载：G.FMT.03` | `经 common 加载：G.FMT.03` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.04` | 保留 common | `经 common 加载：G.FMT.04` | `经 common 加载：G.FMT.04` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.05` | 保留 common | `经 common 加载：G.FMT.05` | `经 common 加载：G.FMT.05` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.06` | 保留 common | `经 common 加载：G.FMT.06` | `经 common 加载：G.FMT.06` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.07` | 保留 common | `经 common 加载：G.FMT.07` | `经 common 加载：G.FMT.07` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.08` | 保留 common | `经 common 加载：G.FMT.08` | `经 common 加载：G.FMT.08` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.09` | 保留 common | `经 common 加载：G.FMT.09` | `经 common 加载：G.FMT.09` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.10` | 保留 common | `经 common 加载：G.FMT.10` | `经 common 加载：G.FMT.10` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.11` | 保留 common | `经 common 加载：G.FMT.11` | `经 common 加载：G.FMT.11` | 两端使用相同的治理条件和整改原则。 |
| `G.FMT.12` | 保留 common | `经 common 加载：G.FMT.12` | `经 common 加载：G.FMT.12` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.FMT.13` | 保留 common | `经 common 加载：G.FMT.13` | `经 common 加载：G.FMT.13` | 两端使用相同的治理条件和整改原则。 |
| `G.NAM.01` | 拆分 | `MYSQL-NAM-001` | `POSTGRESQL-NAM-001` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.02` | 保留 common | `经 common 加载：G.NAM.02` | `经 common 加载：G.NAM.02` | 两端使用相同的治理条件和整改原则。 |
| `G.NAM.03` | 拆分 | `MYSQL-NAM-003` | `POSTGRESQL-NAM-003` | 底层边界涉及 identifiers/reserved words；按双方言官方规范分别判定。 |
| `G.NAM.04` | 保留 common | `经 common 加载：G.NAM.04` | `经 common 加载：G.NAM.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.05` | 保留 common | `经 common 加载：G.NAM.05` | `经 common 加载：G.NAM.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.06` | 保留 common | `经 common 加载：G.NAM.06` | `经 common 加载：G.NAM.06` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.NAM.07` | 保留 common | `经 common 加载：G.NAM.07` | `经 common 加载：G.NAM.07` | 两端使用相同的治理条件和整改原则。 |
| `G.NAM.08` | 保留 common | `经 common 加载：G.NAM.08` | `经 common 加载：G.NAM.08` | 两端使用相同的治理条件和整改原则。 |
| `G.NAM.09` | 保留 common | `经 common 加载：G.NAM.09` | `经 common 加载：G.NAM.09` | 两端使用相同的治理条件和整改原则。 |
| `G.CMT.01` | 保留 common | `经 common 加载：G.CMT.01` | `经 common 加载：G.CMT.01` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.02` | 保留 common | `经 common 加载：G.CMT.02` | `经 common 加载：G.CMT.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.03` | 保留 common | `经 common 加载：G.CMT.03` | `经 common 加载：G.CMT.03` | 两端使用相同的治理条件和整改原则。 |
| `G.CMT.04` | 保留 common | `经 common 加载：G.CMT.04` | `经 common 加载：G.CMT.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.05` | 保留 common | `经 common 加载：G.CMT.05` | `经 common 加载：G.CMT.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.06` | 保留 common | `经 common 加载：G.CMT.06` | `经 common 加载：G.CMT.06` | 两端使用相同的治理条件和整改原则。 |
| `G.CMT.07` | 保留 common | `经 common 加载：G.CMT.07` | `经 common 加载：G.CMT.07` | 两端使用相同的治理条件和整改原则。 |
| `G.CMT.08` | 保留 common | `经 common 加载：G.CMT.08` | `经 common 加载：G.CMT.08` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.09` | 保留 common | `经 common 加载：G.CMT.09` | `经 common 加载：G.CMT.09` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.CMT.10` | 保留 common | `经 common 加载：G.CMT.10` | `经 common 加载：G.CMT.10` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.SEL.01` | 拆分 | `MYSQL-SEL-001` | `POSTGRESQL-SEL-001` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.02` | 保留 common | `经 common 加载：G.SEL.02` | `经 common 加载：G.SEL.02` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.03` | 保留 common | `经 common 加载：G.SEL.03` | `经 common 加载：G.SEL.03` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.04` | 保留 common | `经 common 加载：G.SEL.04` | `经 common 加载：G.SEL.04` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.05` | 拆分 | `MYSQL-SEL-005` | `POSTGRESQL-SEL-005` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.06` | 保留 common | `经 common 加载：G.SEL.06` | `经 common 加载：G.SEL.06` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.07` | 保留 common | `经 common 加载：G.SEL.07` | `经 common 加载：G.SEL.07` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.08` | 拆分 | `MYSQL-SEL-008` | `POSTGRESQL-SEL-008` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.09` | 保留 common | `经 common 加载：G.SEL.09` | `经 common 加载：G.SEL.09` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.10` | 保留 common | `经 common 加载：G.SEL.10` | `经 common 加载：G.SEL.10` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.11` | 保留 common | `经 common 加载：G.SEL.11` | `经 common 加载：G.SEL.11` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.12` | 拆分 | `MYSQL-GSEL-012` | `POSTGRESQL-GSEL-012` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.13` | 保留 common | `经 common 加载：G.SEL.13` | `经 common 加载：G.SEL.13` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.14` | 保留 common | `经 common 加载：G.SEL.14` | `经 common 加载：G.SEL.14` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.15` | 保留 common | `经 common 加载：G.SEL.15` | `经 common 加载：G.SEL.15` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.16` | 保留 common | `经 common 加载：G.SEL.16` | `经 common 加载：G.SEL.16` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.17` | 拆分 | `MYSQL-SEL-017` | `POSTGRESQL-SEL-017` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.SEL.18` | 保留 common | `经 common 加载：G.SEL.18` | `经 common 加载：G.SEL.18` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.19` | 保留 common | `经 common 加载：G.SEL.19` | `经 common 加载：G.SEL.19` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.20` | 保留 common | `经 common 加载：G.SEL.20` | `经 common 加载：G.SEL.20` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.21` | 保留 common | `经 common 加载：G.SEL.21` | `经 common 加载：G.SEL.21` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.22` | 保留 common | `经 common 加载：G.SEL.22` | `经 common 加载：G.SEL.22` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.23` | 保留 common | `经 common 加载：G.SEL.23` | `经 common 加载：G.SEL.23` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.24` | 保留 common | `经 common 加载：G.SEL.24` | `经 common 加载：G.SEL.24` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.25` | 保留 common | `经 common 加载：G.SEL.25` | `经 common 加载：G.SEL.25` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.26` | 保留 common | `经 common 加载：G.SEL.26` | `经 common 加载：G.SEL.26` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.27` | 保留 common | `经 common 加载：G.SEL.27` | `经 common 加载：G.SEL.27` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.28` | 保留 common | `经 common 加载：G.SEL.28` | `经 common 加载：G.SEL.28` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.29` | 保留 common | `经 common 加载：G.SEL.29` | `经 common 加载：G.SEL.29` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.30` | 保留 common | `经 common 加载：G.SEL.30` | `经 common 加载：G.SEL.30` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.31` | 保留 common | `经 common 加载：G.SEL.31` | `经 common 加载：G.SEL.31` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.32` | 保留 common | `经 common 加载：G.SEL.32` | `经 common 加载：G.SEL.32` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.33` | 保留 common | `经 common 加载：G.SEL.33` | `经 common 加载：G.SEL.33` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.34` | 保留 common | `经 common 加载：G.SEL.34` | `经 common 加载：G.SEL.34` | 两端使用相同的治理条件和整改原则。 |
| `G.SEL.35` | 拆分 | `MYSQL-SEL-035` | `POSTGRESQL-SEL-035` | 底层边界涉及 SELECT/functions/operators/optimizer；按双方言官方规范分别判定。 |
| `G.INS.01` | 拆分 | `MYSQL-GINS-001` | `POSTGRESQL-GINS-001` | 底层边界涉及 INSERT/coercion；按双方言官方规范分别判定。 |
| `G.INS.02` | 保留 common | `经 common 加载：G.INS.02` | `经 common 加载：G.INS.02` | 两端使用相同的治理条件和整改原则。 |
| `G.INS.03` | 保留 common | `经 common 加载：G.INS.03` | `经 common 加载：G.INS.03` | 两端使用相同的治理条件和整改原则。 |
| `G.DEL.01` | 拆分 | `MYSQL-GDEL-001`、`MYSQL-DEL-002` | `POSTGRESQL-GDEL-001`、`POSTGRESQL-DEL-002` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.DEL.02` | 拆分 | `MYSQL-UPD-001` | `POSTGRESQL-UPD-001` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.DEL.03` | 拆分 | `MYSQL-DEL-003` | `POSTGRESQL-DEL-003` | 底层边界涉及 DELETE grammar/locking；按双方言官方规范分别判定。 |
| `G.UPD.01` | 拆分 | `MYSQL-GUPD-001` | `POSTGRESQL-GUPD-001` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.02` | 拆分 | `MYSQL-UPD-002` | `POSTGRESQL-UPD-002` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.03` | 拆分 | `MYSQL-UPD-001` | `POSTGRESQL-UPD-001` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.04` | 保留 common | `经 common 加载：G.UPD.04` | `经 common 加载：G.UPD.04` | 两端使用相同的治理条件和整改原则。 |
| `G.UPD.05` | 拆分 | `MYSQL-UPD-005` | `POSTGRESQL-UPD-005` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.06` | 拆分 | `MYSQL-UPD-006` | `POSTGRESQL-UPD-006` | 底层边界涉及 UPDATE grammar/evaluation；按双方言官方规范分别判定。 |
| `G.UPD.07` | 保留 common | `经 common 加载：G.UPD.07` | `经 common 加载：G.UPD.07` | 两端使用相同的治理条件和整改原则。 |
| `G.CLI.01` | 保留 common | `经 common 加载：G.CLI.01` | `经 common 加载：G.CLI.01` | 两端使用相同的治理条件和整改原则。 |
| `G.CLI.02` | 保留 common | `经 common 加载：G.CLI.02` | `经 common 加载：G.CLI.02` | 两端使用相同的治理条件和整改原则。 |
| `G.CLI.03` | 保留 common | `经 common 加载：G.CLI.03` | `经 common 加载：G.CLI.03` | 两端使用相同的治理条件和整改原则。 |
| `G.CLI.04` | 保留 common | `经 common 加载：G.CLI.04` | `经 common 加载：G.CLI.04` | 两端使用相同的治理条件和整改原则。 |
| `G.CLI.05` | 保留 common | `经 common 加载：G.CLI.05` | `经 common 加载：G.CLI.05` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.01` | 拆分 | `MYSQL-GTXN-001` | `POSTGRESQL-GTXN-001` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.02` | 保留 common | `经 common 加载：G.TXN.02` | `经 common 加载：G.TXN.02` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.03` | 保留 common | `经 common 加载：G.TXN.03` | `经 common 加载：G.TXN.03` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.04` | 保留 common | `经 common 加载：G.TXN.04` | `经 common 加载：G.TXN.04` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.05` | 保留 common | `经 common 加载：G.TXN.05` | `经 common 加载：G.TXN.05` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.06` | 保留 common | `经 common 加载：G.TXN.06` | `经 common 加载：G.TXN.06` | 两端使用相同的治理条件和整改原则。 |
| `G.TXN.07` | 拆分 | `MYSQL-TXN-007` | `POSTGRESQL-TXN-007` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.TXN.08` | 拆分 | `MYSQL-TXN-008` | `POSTGRESQL-TXN-008` | 底层边界涉及 transactions/locking；按双方言官方规范分别判定。 |
| `G.UPG.01` | 保留 common | `经 common 加载：G.UPG.01` | `经 common 加载：G.UPG.01` | 两端使用相同的治理条件和整改原则。 |
| `G.UPG.02` | 拆分 | `MYSQL-UPG-002` | `POSTGRESQL-UPG-002` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.03` | 拆分 | `MYSQL-GUPG-003` | `POSTGRESQL-GUPG-003` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.04` | 拆分 | `MYSQL-PART-001` | `POSTGRESQL-PART-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.05` | 拆分 | `MYSQL-UPG-005` | `POSTGRESQL-UPG-005` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.06` | 保留 common | `经 common 加载：G.UPG.06` | `经 common 加载：G.UPG.06` | 两端使用相同的治理条件和整改原则。 |
| `G.UPG.07` | 拆分 | `MYSQL-UPG-007` | `POSTGRESQL-UPG-007` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.08` | 拆分 | `MYSQL-UPG-008` | `POSTGRESQL-UPG-008` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.09` | 保留 common | `经 common 加载：G.UPG.09` | `经 common 加载：G.UPG.09` | 两端使用相同的治理条件和整改原则。 |
| `G.UPG.10` | 拆分 | `MYSQL-GUPG-010` | `POSTGRESQL-GUPG-010` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.11` | 拆分 | `MYSQL-GUPG-011` | `POSTGRESQL-GUPG-011` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.12` | 拆分 | `MYSQL-DDL-001` | `POSTGRESQL-DDL-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.UPG.13` | 拆分 | `MYSQL-DDL-001` | `POSTGRESQL-DDL-001` | 底层边界涉及 ALTER/online DDL；按双方言官方规范分别判定。 |
| `G.SEC.01` | 保留 common | `经 common 加载：G.SEC.01` | `经 common 加载：G.SEC.01` | 两端使用相同的治理条件和整改原则。 |
| `G.SEC.02` | 保留 common | `经 common 加载：G.SEC.02` | `经 common 加载：G.SEC.02` | 两端使用相同的治理条件和整改原则。 |
| `G.SEC.03` | 保留 common | `经 common 加载：G.SEC.03` | `经 common 加载：G.SEC.03` | 两端使用相同的治理条件和整改原则。 |
| `G.KOO.01` | 保留 common | `经 common 加载：G.KOO.01` | `经 common 加载：G.KOO.01` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.02` | 保留 common | `经 common 加载：G.KOO.02` | `经 common 加载：G.KOO.02` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.03` | 保留 common | `经 common 加载：G.KOO.03` | `经 common 加载：G.KOO.03` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.04` | 保留 common | `经 common 加载：G.KOO.04` | `经 common 加载：G.KOO.04` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.05` | 保留 common | `经 common 加载：G.KOO.05` | `经 common 加载：G.KOO.05` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.06` | 保留 common | `经 common 加载：G.KOO.06` | `经 common 加载：G.KOO.06` | 两端使用相同的治理条件和整改原则。 |
| `G.KOO.07` | 保留 common | `经 common 加载：G.KOO.07` | `经 common 加载：G.KOO.07` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.08` | 保留 common | `经 common 加载：G.KOO.08` | `经 common 加载：G.KOO.08` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |
| `G.KOO.09` | 保留 common | `经 common 加载：G.KOO.09` | `经 common 加载：G.KOO.09` | 纯组织、文本格式或发布归档约束；判定不读取数据库方言语义。 |

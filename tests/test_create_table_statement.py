"""Tests parsing of create table statements"""

from dbsync.parsing.statement_processor import process_statements
from dbsync.settings import Settings

DB_NAME = "dbsync_test"
TBL_PREFIX = "tbl_"
TBL_NAME = "tbl_test0"


class TestCreateTableStatement:
    def test_myphpadmin_style(self):
        sql = [
            f"USE `{DB_NAME}`;",
            """CREATE TABLE `tbl_test0` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
"""
        ]

        self._pretest_setup()
        table = self._get_table(sql)
        assert table.name == TBL_NAME
        assert len(table.columns) == 3

    # TODO test table with multi-column PK 
    def test_mysql_workbench_style(self):
        sql = [
            f"USE `{DB_NAME}`;",
            """CREATE TABLE `tbl_test0` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
"""
        ]
        table_modifiers = "ENGINE=InnoDB AUTO_INCREMENT=10 \
DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci"

        self._pretest_setup()
        table = self._get_table(sql)
        assert table.name == TBL_NAME, f"Table should be named '{TBL_NAME}'"
        assert len(table.columns) == 3, "Table should have 3 columns"
        col = table.get_column("id")
        assert col.auto_inc, "Table should have auto_increment"
        assert col.auto_inc_val == 10, "Table auto-increment value should be 10"
        assert len(table.primary_keys) == 1, "Table should have primary key"
        assert table.primary_keys[0] == "id", "Table primary key should be 'id'"
        assert table.post_definition_modifiers == table_modifiers, "Table should have modifiers"

    # TODO add test for:
    sql_with_key = """CREATE TABLE `NhU_actionscheduler_claims` (
  `claim_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`claim_id`),
  KEY `date_created_gmt` (`date_created_gmt`)
) ENGINE=InnoDB AUTO_INCREMENT=8257 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
"""

    def _get_table(self, sql):
        repo = process_statements(sql, DB_NAME)
        repo.post_process()
        print(repr(repo))
        return repo.get_table(TBL_NAME)

    def setup_method(self, test_method):
        # further proof that singletons are a bad idea:
        self.saved_settings = Settings.obj().copy()

    def _pretest_setup(self):
        # this is kludgy:
        settings = Settings.obj()
        settings.db_name = DB_NAME
        settings.tbl_prefix = TBL_PREFIX
        settings.init()

    def teardown_method(self, test_method):
        settings = Settings.obj()
        settings.db_name = self.saved_settings.db_name
        settings.tbl_prefix = self.saved_settings.tbl_prefix
        settings.init()

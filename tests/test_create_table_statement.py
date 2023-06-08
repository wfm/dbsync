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
            # TODO should "unsigned" be part of the datatype or the modifiers?
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
    sql_with_key = """CREATE TABLE `tbl_test0` (
  `claim_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`claim_id`),
  KEY `date_created_gmt` (`date_created_gmt`)
) ENGINE=InnoDB AUTO_INCREMENT=8257 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
"""
    def test_mysql_workbench_style_with_keys(self):
        sql = [
            f"USE `{DB_NAME}`;",
            """CREATE TABLE `tbl_test0` (
  `claim_id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `random` varchar(255) NOT NULL,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`claim_id`),
  KEY `date_created_gmt` (`date_created_gmt`),
  UNIQUE KEY `random_claim_key` (`random`(10), `claim_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8257 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
"""
        ]

        self._pretest_setup()
        table = self._get_table(sql)
        assert len(table.primary_keys) == 1, "Table should have primary key"
        assert table.primary_keys[0] == "claim_id", "Table primary key should be 'id'"
        assert len(table.keys) == 3, "Table should have 3 keys"
        # Assuming the keys are in the order they occur in the SQL
        assert table.keys[0].name == "", "PK has no name"
        assert table.keys[0].is_primary, "Should be primary key"
        assert not table.keys[0].is_unique, "Should not be a UNIQUE key"
        assert len(table.keys[0].columns) == 1, "PK should have 1 column"
        assert table.keys[0].columns[0].name == "claim_id", "PK column should be named 'claim_id"
        assert table.keys[0].columns[0].length is None, "PK column should not have a length"

        assert table.keys[1].name == "date_created_gmt", "Key should be named 'date_created_gmt'"
        assert not table.keys[1].is_primary, "Should not be primary key"
        assert not table.keys[1].is_unique, "Should not be a UNIQUE key"
        assert len(table.keys[1].columns) == 1, "'date_created_gmt' should have 1 column"
        assert table.keys[1].columns[0].name == "date_created_gmt", "Key column should be named 'date_created_gmt"
        assert table.keys[1].columns[0].length is None, "Key column should not have a length"

        assert table.keys[2].name == "random_claim_key", "Key should be named 'random_claim_key'"
        assert not table.keys[2].is_primary, "Should not be primary key"
        assert table.keys[2].is_unique, "Should be a UNIQUE key"
        assert len(table.keys[2].columns) == 2, "'random_claim_key' should have 2 columns"
        assert table.keys[2].columns[0].name == "random", "Key column 1 should be named 'random"
        assert table.keys[2].columns[0].length == 10, "Key column 1 have length of 10"
        assert table.keys[2].columns[1].name == "claim_id", "Key column 2 should be named 'claim_id"
        assert table.keys[2].columns[1].length is None, "Key column 2 should not have a length"

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

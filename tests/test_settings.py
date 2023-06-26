"""Test the Settings module"""

import re

from dbsync.settings import Settings


class TestSettings:
    tbl_base = "test1"
    timestamp_cols = {
        tbl_base: ["date_created_gmt"]
    }

    def setup_method(self, test_method):
        # further proof that singletons are a bad idea:
        self.saved_settings = Settings.obj().copy()
        settings = Settings.obj()
        settings.timestamp_cols = TestSettings.timestamp_cols
        settings.src_prefix, settings.dst_prefix = settings.dst_prefix, settings.src_prefix
        settings.init()

    def teardown_method(self, test_method):
        settings = Settings.obj()
        settings.timestamp_cols = self.saved_settings.timestamp_cols
        settings.init()

    def test_timestamp_cols1(self):
        actual = Settings.obj().timestamp_cols[TestSettings.tbl_base]
        self._timestamp_assert(actual)

    def test_timestamp_cols2(self):
        tbl_name = f"{Settings.obj().src_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        actual = Settings.obj().get_timestamp_cols(tbl_name)
        self._timestamp_assert(actual)

    def test_timestamp_cols3(self):
        tbl_name = f"{Settings.obj().dst_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        actual = Settings.obj().get_timestamp_cols(tbl_name)
        self._timestamp_assert(actual)

    def _timestamp_assert(self, actual):
        assert actual == TestSettings.timestamp_cols[TestSettings.tbl_base]

    def test_reversed_prefixes_src(self):
        src_tbl_name = f"{Settings.obj().src_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        assert not Settings.obj().is_dst_table(src_tbl_name)
        assert Settings.obj().is_src_table(src_tbl_name)
        pattern = Settings.obj().get_test_table_name_pattern()
        assert re.search(pattern, src_tbl_name) is not None
        assert TestSettings.tbl_base == Settings.obj().get_base_table_name(src_tbl_name)
        expected_tbl_name = f"{Settings.obj().src_prefix}{Settings.obj().tbl_prefix}expected"
        actual_tbl_name = Settings.obj().patch_table_name("expected", src_tbl_name)
        assert actual_tbl_name == expected_tbl_name

    def test_reversed_prefixes_dst(self):
        dst_tbl_name = f"{Settings.obj().dst_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        assert Settings.obj().is_dst_table(dst_tbl_name)
        assert not Settings.obj().is_src_table(dst_tbl_name)
        pattern = Settings.obj().get_test_table_name_pattern()
        assert re.search(pattern, dst_tbl_name) is None
        assert TestSettings.tbl_base == Settings.obj().get_base_table_name(dst_tbl_name)
        expected_tbl_name = f"{Settings.obj().dst_prefix}{Settings.obj().tbl_prefix}expected"
        actual_tbl_name = Settings.obj().patch_table_name("expected", dst_tbl_name)
        assert actual_tbl_name == expected_tbl_name



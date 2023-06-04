"""Test the Settings module"""

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
        settings.init()

    def teardown_method(self, test_method):
        settings = Settings.obj()
        settings.timestamp_cols = self.saved_settings.timestamp_cols
        settings.init()

    def test_timestamp_cols1(self):
        actual = Settings.obj().timestamp_cols[TestSettings.tbl_base]
        self._assert(actual)

    def test_timestamp_cols2(self):
        tbl_name = f"{Settings.obj().src_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        actual = Settings.obj().get_timestamp_cols(tbl_name)
        self._assert(actual)

    def test_timestamp_cols3(self):
        tbl_name = f"{Settings.obj().dst_prefix}{Settings.obj().tbl_prefix}{TestSettings.tbl_base}"
        actual = Settings.obj().get_timestamp_cols(tbl_name)
        self._assert(actual)

    def _assert(self, actual):
        assert actual == TestSettings.timestamp_cols[TestSettings.tbl_base]

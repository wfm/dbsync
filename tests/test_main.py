"""Integration Tests"""

from difflib import Differ
from io import StringIO
from pathlib import Path
from typing import List

from dbsync.settings import Settings, SyncActions
from dbsync.main import do_comparison

DIRECTORY = "./tests/data"
DB_NAME = "dbsync_test"
TBL_PREFIX = "tbl_"

#
# inserts with unequal numbers of rows
# updates with various numbers of columns changing
# multiple insert statements in different orders
# inserts with rows in different order
# creating a table
# updates with timestamps
# unique keys


class TestMain:
    def test_runner(self):
        files = self._get_test_files()
        for pair in files:
            self._pretest_setup()
            do_comparison(pair[0])
            self._test_output(pair[1])

    # TODO can we get this from a file?
    timestamp_cols = {
        "test1": ["date_created_gmt"]
    }

    def setup_method(self, test_method):
        # further proof that singletons are a bad idea:
        self.saved_settings = Settings.obj().copy()

    def _pretest_setup(self):
        self.fd = StringIO()
        # this is kludgy:
        settings = Settings.obj()
        settings.db_name = DB_NAME
        settings.tbl_prefix = TBL_PREFIX
        settings.output_file = None
        settings.file_descriptor = self.fd
        settings.default_sync_action = SyncActions.MERGE
        settings.timestamp_cols = TestMain.timestamp_cols
        settings.init()

    def teardown_method(self, test_method):
        settings = Settings.obj()
        settings.db_name = self.saved_settings.db_name
        settings.tbl_prefix = self.saved_settings.tbl_prefix
        settings.output_file = self.saved_settings.output_file
        settings.file_descriptor = self.saved_settings.file_descriptor
        settings.default_sync_action = self.saved_settings.default_sync_action
        settings.timestamp_cols = self.saved_settings.timestamp_cols
        settings.init()

    def _get_test_files(self):
        path = Path(DIRECTORY)
        files = [f for f in path.iterdir() if f.is_file()]
        files.sort(key=lambda f: f.name)
        inf = [f for f in files if f.name.endswith("-input.sql")]
        outf = [f for f in files if f.name.endswith("-expected-output.sql")]
        assert len(inf) == len(outf)

        for idx in range(0, len(inf)):
            prefix = f"test{idx}"
            assert inf[idx].name.startswith(prefix)
            assert outf[idx].name.startswith(prefix)

        in_names = [str(f) for f in inf]
        return list(zip(in_names, outf))

    def _test_output(self, expected_file: Path) -> None:
        expected = expected_file.read_text()
        actual = self.fd.getvalue()
        self.fd.close()
        expected_clean = self._cleanup_output(expected)
        actual_clean = self._cleanup_output(actual)
        # TODO this was charjunk=" ", but that made the enumeration of c blow up
        d = Differ(charjunk=None)
        c = d.compare(actual_clean, expected_clean)
        errs = [line for line in c if not line.startswith(" ")]
        if len(errs) > 0:
            print("\n".join(list(errs)))
            raise AssertionError(f"Test with {expected_file.name} failed")

    def _cleanup_output(self, text: str) -> List[str]:
        # split into lines and remove comments
        # TODO do we need to remove /* ... */ style comments?
        lines = text.splitlines()
        filtered = [line for line in lines if not line.startswith("--")]
        return filtered

"""Integration Tests"""

from difflib import Differ
from io import StringIO
from pathlib import Path
from typing import List

from dbsync.settings import Settings
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


class TestMain:
    def test_runner(self):
        files = self._get_test_files()
        for pair in files:
            self.fd.truncate()
            do_comparison(pair[0])
            self._test_output(pair[1])

    def setup_method(self, test_method):
        # further proof that singletons are a bad idea:
        self.saved_settings = Settings.obj().copy()
        self.fd = StringIO()
        # this is kludgy:
        settings = Settings.obj()
        settings.db_name = DB_NAME
        settings.tbl_prefix = TBL_PREFIX
        settings.output_file = None
        settings.file_descriptor = self.fd
        settings.init()

    def teardown_method(self, test_method):
        settings = Settings.obj()
        settings.db_name = self.saved_settings.db_name
        settings.tbl_prefix = self.saved_settings.tbl_prefix
        settings.output_file = self.saved_settings.output_file
        settings.file_descriptor = self.saved_settings.file_descriptor
        settings.init()

    def _get_test_files(self):
        path = Path(DIRECTORY)
        files = [f for f in path.iterdir() if f.is_file()]
        inf = [f for f in files if f.name.endswith("-input.sql")]
        outf = [f for f in files if f.name.endswith("-expected-output.sql")]
        for idx in range(0, len(inf)):
            prefix = f"test{idx}"
            if not inf[idx].name.startswith(prefix) or \
               not outf[idx].name.startswith(prefix):
                print(f"Missing a test file, index {idx}")
                exit(1)
        in_names = [str(f) for f in inf]
        return list(zip(in_names, outf))

    def _test_output(self, expected_file: Path) -> None:
        expected = expected_file.read_text()
        actual = self.fd.getvalue()
        self.fd.close()
        expected_clean = self._cleanup_output(expected)
        actual_clean = self._cleanup_output(actual)
        d = Differ(charjunk=" ")
        c = d.compare(actual_clean, expected_clean)
        errs = [line for line in c if not line.startswith(" ")]
        if len(errs) > 0:
            print("\n".join(list(errs)))
            assert False, f"^^^^^ Test with {expected_file.name} failed"

    def _cleanup_output(self, text: str) -> List[str]:
        # split into lines and remove comments
        lines = text.splitlines()
        filtered = [line for line in lines if not line.startswith("--")]
        return filtered

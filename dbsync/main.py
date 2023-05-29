import argparse
import time

import sqlparse

from dbsync.settings import Settings
from dbsync.parsing.statement_processor import process_statements
from dbsync.comparing.comparison import Comparison


#
# Databases
#   maryjoya_WP5Z2
#   maryjoya_WPAJC
#   maryjoya_WPKWA
def get_args():
    settings = Settings()

    argparser = argparse.ArgumentParser(
        prog="dbsync",
        description="Generates SQL to sync prod DB to staging DB",
        epilog="So long, and thanks for playing"
    )

    argparser.add_argument(
        "filename",
        help="The input file, a SQL dump from MySQL")
    argparser.add_argument(
        "-d", "--database",
        help="The name of the database to sync",
        default=settings.db_name)
    argparser.add_argument(
        "-o", "--output",
        help="The filename for the SQL output",
        default=settings.output_file)

    args = argparser.parse_args()
    settings.db_name = args.database
    settings.output_file = args.output
    Settings.obj(settings)
    print("dbsync from   :", args.filename)
    print("  database    :", args.database)
    print("  output file :", args.output)
    return args.filename


def main():
    filename = get_args()
    time0 = time.time()
    with open(filename, "r", encoding="utf8") as f:
        text_l = sqlparse.split(f.read())
    time1 = time.time()
    repo = process_statements(text_l, Settings.obj().db_name)
    time2 = time.time()
    repo.post_process()
    time3 = time.time()
    c = Comparison(repo, Settings.obj().output_file)
    c.compare()
    time4 = time.time()

    print("Timing:")
    print("  Read and split file : %.2f" % (time1-time0))
    print("  Process statements  : %.2f" % (time2-time1))
    print("  Post-Processing     : %.2f" % (time3-time2))
    print("  Compare and output  : %.2f" % (time4-time3))
    print("  Total               : %.2f" % (time4-time0))

    return 0

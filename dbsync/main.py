import argparse
import time

import sqlparse

from dbsync.settings import Settings, SyncActions
from dbsync.parsing.statement_processor import process_statements
from dbsync.comparing.comparison import Comparison
from dbsync.parsing.splitter import Splitter


#
# Databases and table prefixs
#   maryjoya_WP5Z2  NhU_
#   maryjoya_WPAJC
#   maryjoya_WPKWA  EMk_
def get_args():
    settings = Settings()

    argparser = argparse.ArgumentParser(
        prog="dbsync",
        description="Generates SQL to sync prod DB to staging DB"
        #epilog="So long, and thanks for all the fish!"
    )

    argparser.add_argument(
        "filename",
        help="The input file, a SQL dump from MySQL")
    argparser.add_argument(
        "-d", "--database",
        help="The name of the database to sync",
        default=settings.db_name)
    argparser.add_argument(
        "-t", "--table_prefix",
        help="The Wordpress table prefix",
        default=settings.tbl_prefix)
    argparser.add_argument(
        "--timestamp",
        help="Info to add to timestamp columns, e.g. tbl1=col1,col2;tbl2=col3",
        default="")
    argparser.add_argument(
        "--only",
        help="Only process the listed tables, e.g., tbl1,tbl2,tbl3",
        default=""
    )
    argparser.add_argument(
        "-da", "--default_action",
        help="Default action for how to process tables",
        choices=["DEFAULT", "SKIP", "COPY", "MERGE"],
        default="DEFAULT"
    )
    argparser.add_argument(
        "-v", "--verify",
        help="Skips tables that would otherwise be copied",
        default=False,
        action="store_true")
    argparser.add_argument(
        "-hw", "--highwater",
        help="Also writes high water mark file",
        default=False,
        action="store_true"
    )
    argparser.add_argument(
        "--split",
        help="Split sql into separate files for src and dst",
        default=False,
        action="store_true"
    )
    argparser.add_argument(
        "-o", "--output",
        help="The filename for the SQL output",
        default=settings.output_file)
    argparser.add_argument(
        "-q", "--quiet",
        help="Suppresses output to stdout",
        default=False,
        action="store_true")

    args = argparser.parse_args()

    if len(args.timestamp) > 0:
        pairs = [x.split("=") for x in args.timestamp.replace(" ", "").split(";")]
        for p in pairs:
            p[1] = p[1].split(",")
        d = dict(pairs)
        print("Timestamp cols:", d)
        settings.timestamp_cols.update(d)

    only_tables = len(args.only) > 0
    if only_tables:
        tables = [settings.get_base_table_name(t) for t in args.only.replace(" ", "").split(",")]
        settings.included_tables += tables
# default_sync_action
    settings.db_name = args.database
    settings.tbl_prefix = args.table_prefix
    settings.default_sync_action = SyncActions[args.default_action]
    settings.output_file = args.output
    settings.verify_mode = args.verify
    settings.verbose_mode = not args.quiet
    Settings.obj(settings)
    if not args.quiet:
        if args.verify:
            print("VERIFY MODE")
        print("dbsync from    :", args.filename)
        print("  database     :", args.database)
        print("  table prefix :", args.table_prefix)
        if args.default_action != "DEFAULT":
            print("default action :", args.default_action)
        print("  output file  :", args.output)
        if only_tables:
            print("   only tables :", tables)
    return (args.filename, args.quiet, args.highwater, args.split)


def main():
    filename, quiet, highwater, split = get_args()
    if split:
        do_split(filename)
    else:
        do_comparison(filename, quiet, highwater)
    return 0


def do_comparison(filename: str, quiet=True, highwater=False) -> None:
    time0 = time.time()
    with open(filename, "r", encoding="utf8") as f:
        text_l = sqlparse.split(f.read())
    time1 = time.time()
    repo = process_statements(text_l, Settings.obj().db_name)
    time2 = time.time()
    repo.post_process()
    time3 = time.time()
    c = Comparison(repo, Settings.obj().output_file, Settings.obj().file_descriptor)
    if highwater:
        c.write_high_water_marks()
    else:
        c.compare()
    time4 = time.time()

    if not quiet:
        print("Timing:")
        print("  Read and split file : %.2f" % (time1 - time0))
        print("  Process statements  : %.2f" % (time2 - time1))
        print("  Post-Processing     : %.2f" % (time3 - time2))
        print("  Compare and output  : %.2f" % (time4 - time3))
        print("  Total               : %.2f" % (time4 - time0))


def do_split(filename: str) -> None:
    with open(filename, "r", encoding="utf8") as f:
        text_l = sqlparse.split(f.read())
    split = Splitter()
    split.separate_statements(text_l)

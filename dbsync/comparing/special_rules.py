"""functions to handle changes to data made when the staging site was created"""

# Note: I copied the source into Settings because there was a circular reference
# Someday, I will refactor Settings
import re

from dbsync.settings import Settings


def alter_table_name(value: str) -> str:
    pattern = f"(?<!{Settings.obj().dst_prefix}){Settings.obj().tbl_prefix}"
    repl = f"{Settings.obj().dst_prefix}{Settings.obj().tbl_prefix}"
    return re.sub(pattern, repl, value)


def alter_site_url(value: str) -> str:
    src_uri = Settings.obj().base_uri
    dst_uri = Settings.obj().base_uri + Settings.obj().stage_uri_path
    return value.replace(src_uri, dst_uri)

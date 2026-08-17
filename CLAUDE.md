# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python CLI tool (`dbsync`) that generates SQL to sync data between a WordPress production MySQL database and a Bluehost-managed staging database. Bluehost's staging feature prefixes staging tables with `staging_`, so prod tables (`NhU_posts`) and staging tables (`staging_NhU_posts`) coexist in the same database. This tool reads a `mysqldump` of the database, compares the two sets of tables, and writes a SQL script that updates the staging tables to match prod (or vice versa).

## Commands

```bash
# Activate the virtual environment first
source venv/bin/activate

# Run the tool
python -m dbsync <dump.sql> [options]
python -m dbsync <dump.sql> -c dbsync_prod_to_local.json   # use config file
python -m dbsync <dump.sql> -c dbsync_to_prod.json --split  # split into src/dst files

# Run all tests
pytest

# Run a single test file
pytest tests/test_comparison.py

# Run with lint
pylint dbsync/
```

## Architecture

The pipeline has three stages:

**1. Parse** (`dbsync/parsing/`)  
`Splitter` → can optionally split a dump into separate src/dst SQL files.  
`statement_processor.process_statements()` → walks sqlparse tokens, routing each statement to `create_table`, `insert_data`, or `AlterStatement.parse()`. Everything is collected into a `ComparisonRepo`.

**2. Intermediate Representation** (`dbsync/intermediate.py`)  
All parsed SQL is stored as dataclasses: `Table`, `Column`, `Key`, `Insert`, `KeyList`, `Modification`, `Use`, `Set`. `ComparisonRepo.post_process()` applies ALTER TABLE statements (adding keys and auto-increment info) and coalesces INSERT statements into `UnpackedInsert` objects grouped by table name.

**3. Compare and Output** (`dbsync/comparing/`)  
`Comparison.compare()` iterates tables in FK-dependency order (via `OrderedTableNames`) and calls `_copy_table` or `_merge_table` per table.  
- **COPY**: truncates destination and re-inserts all rows from source.  
- **MERGE**: pairs up source and destination INSERT batches by primary/unique key, diffs them row-by-row via `CompareInsert`, and generates UPDATE/INSERT/DELETE SQL.  
After each table is processed, `_patch_foreign_keys` rewrites FK column values in additions/updates to account for auto-increment ID shifts between the two databases.

## Settings / Configuration

`Settings` (a pydantic `BaseModel`) is a singleton accessed via `Settings.obj()`. It defaults to the maryjoyart.com production configuration. All table-level behavior is configured there:

- `table_options`: per-table `SyncActions` (COPY, MERGE, SKIP, DEFAULT), update modes (OPTIMISTIC/PESSIMISTIC), `synthetic_unique_key` (for tables without a natural unique key), and `special_rules` (column-level transform functions applied during diff).
- `foreign_keys`: the full FK graph; used both for ordering tables and for patching ID values.
- `timestamp_cols`: which columns to use for time-based comparison.
- `src_prefix` / `dst_prefix` / `tbl_prefix`: control which tables are "source" vs "destination".

Config can also be serialized to/from JSON (`-c` flag). The JSON format stores function names as strings; `Settings.init()` re-hydrates them as references to functions in `dbsync/settings.py`.

## Test Structure

Integration tests live in `tests/test_main.py` (`TestMain.test_runner`). They pair `tests/data/testN-input.sql` with `tests/data/testN-expected-output.sql` files. The test harness overrides the global `Settings` singleton (db name, prefix, file descriptor) and compares actual vs expected output, ignoring `--` comment lines.

Unit tests cover individual components: `test_comparison.py`, `test_compare_insert.py`, `test_insert_statement.py`, `test_create_table_statement.py`, `test_alter_statement.py`, `test_keyzip.py`, `test_unpacked_insert.py`, `test_column_list.py`.

**Gotcha**: `Settings` is a global singleton. Tests must save and restore it around each test (see the `setup_method`/`teardown_method` pattern in `TestMain`).

## Key Files

| File | Role |
|------|------|
| `dbsync/settings.py` | All configuration including FK graph and table options |
| `dbsync/intermediate.py` | Dataclass IR for all parsed SQL constructs |
| `dbsync/comparing/comparison.py` | Core diff logic; entry point is `Comparison.compare()` |
| `dbsync/comparing/comparison_repo.py` | Stores parsed state; `post_process()` finalizes it |
| `dbsync/comparing/ordered_table_names.py` | Topological sort of tables by FK dependencies |
| `dbsync/parsing/statement_processor.py` | Walks sqlparse tokens and populates the repo |
| `dbsync/parsing/splitter.py` | Alternative mode: splits dump into src/dst files |
| `dbsync_prod_to_local.json` | Config for syncing staging→local |
| `dbsync_to_prod.json` | Config for syncing staging→prod |

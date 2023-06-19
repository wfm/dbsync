# TODO
## Urgent
* PK errors with synthetic UK
* Integration tests - in progress

## Medium-term
* use ON DUPLICATE KEY UPDATE?
* Key columns may have lengths
* Some "comments" are actually MySQL-specific commands, like /*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
* Refactoring
  - Complexity issues
  - move sql generation into separate modules
  - move classes into separate modules
* Put settings in a file or read them from a file using command line arg
* Use separate InsertRecord and UpdateRecord?
* Linter errors in Github
* After an ALTER TABLE statement, it may be necessary to run ANALYZE TABLE to update index cardinality information. See Section 13.7.7.22, “SHOW INDEX Statement”.

## Future
* Implement stage -> prod
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?
* Prevent SQL injection?
* Generalize the state machine code

#DONE
* Compare stuff that is being updated
* Test with local MySQL
* Sort tables with unique keys by that key before comparing them
* Dumps from MySQL Workbench are different from myPhpAdmin (sp?) - auto inc and pk are part of create table.
* Parse settings at end of create table
* Does it matter that we sort everything like a string when there are numeric PK columns?
* Done: Look at "this is too dumb" in comparison.py
* Done, test: use a timestamp column to decide whether or not to update
* Only output required columns for update statements
* Break up inserts into groups (of 50? 100?)
* Disable/enable auto-increment
* Done: Accept command line args, merge with settings
* Do we need backticks on column names? - added
- increase line length - done
- Get rid of "parser_toy"
* Need ; at end of SET statements
* Summarize diffs to answer questions
* What about tables that don't have a timestamp column? Configure on a table-by-table basis?
* Use ALTER TABLE ... DISABLE KEYS
* Use ALTER TABLE ... AUTO_INCREMENT [=] value
* Do we really need to disable autoinc if our next value is set high enough?
* Check autoincrement
* Use LOCK TABLES `tbl_test0` WRITE; and UNLOCK TABLES?
* Get it to work with dump from MySQL workbench

2023-06-14:
Your theme (Astra Child) contains outdated copies of some WooCommerce template files. These files may need updating to ensure they are compatible with the current version of WooCommerce. Suggestions to fix this:

Update your theme to the latest version. If no update is available contact your theme author asking about compatibility with the current WooCommerce version.
If you copied over a template file to change something, then you will need to copy the new version of the template and apply your changes again.

astra-child/woocommerce/cart/cart-shipping.php,
astra-child/woocommerce/single-product/product-image.php version 3.5.1 is out of date. The core version is 7.8.0

https://woocommerce.com/document/fix-outdated-templates-woocommerce/

--------


Better idea: sort by unique key 
-----------

9587, 442, '_elementor_css', 'a:6:{s:4:\"time\...	9411, 442, '_elementor_css', 'a:6:{s:4:\"time\...
The data for the above is different

===========

    def tuplify(self, x):
        if x is None:
            return None
        elif not isinstance(x, list) or len(x) == 0:
            raise DbSyncCompareException(f"Bad data in tuplify: \"{x}\"")
        elif len(x) == 1:
            return x[0]
        else:
            return tuple(x)

    def appears_later(self, src_item: InsertRecord) -> bool:
        if self.has_unique_key:
            if self.uniq2key is None:
                self._get_unique_column_key_lookup()
            key = self.uniq2key.get(src_item.unique_vals)
            result = key is not None and key > src_item.key
            return result
        return False

    def _get_unique_column_key_lookup(self) -> None:
        if self.has_unique_key and self.uniq2key is None:
            unique_list = [self.tuplify(self.get_unique_vals(v)) for v in self.values]
            key_list = [self.get_key(v) for v in self.values]
            self.uniq2key = dict(zip(unique_list, key_list, strict=True))
        return None

Tables without timestamps that need updating
staging_NhU_postmeta
staging_NhU_termmeta
staging_NhU_term_taxonomy
staging_NhU_usermeta
staging_NhU_wc_product_meta_lookup
staging_NhU_woocommerce_sessions

Check of dbsync run:
MERGE table NhU_postmeta
Updating table staging_NhU_postmeta
  Inserting 111 rows

MERGE table NhU_usermeta
Updating table staging_NhU_usermeta
  Inserting 20 rows

SKIP table NhU_wpforms_payment_meta by DEFAULT
SKIP table NhU_wpforms_payments by DEFAULT


--only NhU_postmeta,NhU_usermeta


Error Code: 1062. Duplicate entry '9331' for key 'staging_nhu_postmeta.PRIMARY'
Error Code: 1100. Table 'NhU_postmeta' was not locked with LOCK TABLES

/*!40000 ALTER TABLE `staging_NhU_postmeta` ENABLE KEYS */;
UNLOCK TABLES;

Error Code: 1064. You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near '9331' at line 1
==============

    def get_ordered_tables(self) -> List[str]:
        def keyfunc(fk: ForeignKey) -> Tuple[str, str]:
            return fk.src_table, fk.src_column

        accumulator = {}
        fks = Settings.obj().foreign_keys
        fks.sort(key=keyfunc)

        def find_fk(key: Tuple[str, str]) -> ForeignKey | None:
            idx = bisect_left(fks, key, key=keyfunc)
            if idx != len(fks) and key == keyfunc(fks[idx]):
                return fks[idx]
            return None

        def accumulate(fk: ForeignKey, level: int = 0):
            print(f"accumulate {fk} ({level})")
            if fk.dst_table in accumulator:
                accumulator[fk.dst_table] += 1
            else:
                accumulator[fk.dst_table] = 1

            if fk.src_table != fk.dst_table:
                next_fk = find_fk((fk.dst_table, fk.dst_column))
                if next_fk is not None:
                    accumulate(next_fk, level + 1)

        for fk in fks:
            accumulate(fk)

        table_names = [Settings.obj().get_base_table_name(x)
                       for x in self.tables.keys()
                       if Settings.obj().is_src_table(x)]
        table_names.sort(reverse=True, key=lambda x: accumulator[x] if x in accumulator else 0)
        return [Settings.obj().get_src_table_name_from_base_name(x) for x in table_names]

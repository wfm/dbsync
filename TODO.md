# TODO
## Urgent
* Integration tests - in progress
* Test with local MySQL

## Medium-term
* Key columns may have lengths
* Some "comments" are actually MySQL-specific commands, like /*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
* Refactoring
  - Complexity issues
  - move sql generation into separate modules
  - move classes into separate modules
* Does it matter that we sort everything like a string when there are numeric PK columns?
- it would be easy to parse the ints...
* Put settings in a file or read them from a file using command line arg
* Parse settings at end of create table
* Use separate InsertRecord and UpdateRecord?
* use ON DUPLICATE KEY UPDATE?
* Linter errors in Github
* Dumps from MySQL Workbench are different from myPhpAdmin (sp?) - auto inc and pk are part of create table.
* If there are more than N diffs, truncate the dst table and reload? But how to tell if src is more recent?
* Generalize the state machine code
* After an ALTER TABLE statement, it may be necessary to run ANALYZE TABLE to update index cardinality information. See Section 13.7.7.22, “SHOW INDEX Statement”.

## Future
* Implement stage -> prod
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?
* Prevent SQL injection?

#DONE
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

LOCK TABLES `staging_tbl_test0` WRITE;
/*!40000 ALTER TABLE `staging_tbl_test0` DISABLE KEYS */;
/*! ALTER TABLE `X` AUTO_INCREMENT=Y */;

/*!40000 ALTER TABLE `staging_tbl_test0` ENABLE KEYS */;
UNLOCK TABLES;

--------
Apparently, the older options get deleted and new options (same option_name, higher option_id)
are inserted into the table.

Do we want to enforce unique keys?
a.) by convoluted sql like where not exists (select 1 from tbl where uniquecol = 'x'), or 
b.) by filtering the data

Other thoughts:
Insert records into dest with higher src id's?
Won't there be overlap of ids in tables where data was added in both systems?

What if we use a dict where the key is the unique columns in the dst table and the value is the primary key
When looking at a src record, check that the dst record doesn't already have a higher pk value

Implemented the above and am getting:
15:06:35	INSERT INTO `staging_NhU_options` (`option_id`, `option_name`, `option_value`, `autoload`) VALUES (66748, 'endurance_cloudflare_enabled', 'basic', 'yes'), (66913, 'wc_connect_error_notice', 'Error retrieving the tax rates. Received (401): {\"statusCode\":401,\"error\":\"Unauthorized\",\"message\":\"Invalid credentials\",\"attributes\":{\"error\":\"Invalid credentials\"}}', 'yes'), **(68456, 'loginlockdown_meta',** 
Error Code: 1062. Duplicate entry 'loginlockdown_meta' for key 'staging_nhu_options.option_name'	0.013 sec

egrep "\(\d+, 'loginlockdown_meta'," ./data/localhost-20230605.sql 
(68456, 'loginlockdown_meta', 'a:3:{s:13:\"first_version\";s:3:\"2.0\";s:13:\"first_install\";i:1681824751;s:12:\"database_ver\";s:4:\"2.06\";}', 'yes'),
(68268, 'loginlockdown_meta', 'a:3:{s:13:\"first_version\";s:3:\"2.0\";s:13:\"first_install\";i:1681915353;s:12:\"database_ver\";s:4:\"2.06\";}', 'yes'), 

I guess if you copy the src to the dst, you need to delete the old src record.
Will there ever be an update?

Better idea: sort by unique key 

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

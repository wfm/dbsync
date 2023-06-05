# TODO
## Urgent
* Integration tests - in progress
* Summarize diffs to answer questions
* Get it to work with dump from MySQL workbench
* What about tables that don't have a timestamp column? Configure on a table-by-table basis?
* Check autoincrement
* Test with local MySQL
* Some "comments" are actually MySQL-specific commands, like /*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
* After an ALTER TABLE statement, it may be necessary to run ANALYZE TABLE to update index cardinality information. See Section 13.7.7.22, “SHOW INDEX Statement”.
* Use ALTER TABLE ... DISABLE KEYS
* Use ALTER TABLE ... AUTO_INCREMENT [=] value
* Do we really need to disable autoinc if our next value is set high enough?

## Medium-term
* Refactoring
  - Complexity issues
  - move sql generation into separate modules
* Does it matter that we sort everything like a string when there are numeric PK columns?
- it would be easy to parse the ints...
* Put settings in a file or read them from a file using command line arg
* Parse settings at end of create table
* Use separate InsertRecord and UpdateRecord?
* use ON DUPLICATE KEY UPDATE?
* Linter errors in Github
* Dumps from MySQL Workbench are different from myPhpAdmin (sp?) - auto inc and pk are part of create table.
* If there are more than N diffs, truncate the dst table and reload? But how to tell if src is more recent?
* Use LOCK TABLES `tbl_test0` WRITE; and UNLOCK TABLES?
* Generalize the state machine code

## Future
* Implement stage -> prod
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?

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


=============
(venv) ➜  dbsync git:(main) ✗ python3 -m dbsync -d dbsync_test -t tbl_ /Users/billmurphy/dumps/Dump20230605a.sql
dbsync from   : /Users/billmurphy/dumps/Dump20230605a.sql
  database    : dbsync_test
  table prefix: tbl_
  output file : output.sql
Table prefix: tbl_
-- db: dbsync_test in_target: True
<class 'dbsync.exceptions.DbSyncParseException'> - Confusion, state: 1, token: <Keyword 'CHARAC...' at 0x101F5E140>
Index: 6
SQL: CREATE TABLE `staging_tbl_test0` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
<class 'dbsync.exceptions.DbSyncParseException'> - Invalid INSERT statement
Index: 4
SQL: INSERT INTO `staging_tbl_test0` VALUES (1,'action-scheduler-migration','2023-06-05 12:11:35'),(2,'wpforms','2023-06-02 07:28:37'),(3,'wc-admin-data','2023-06-02 07:28:37'),(4,'woocommerce-db-updates','2023-06-02 07:28:37'),(5,'woocommerce-remote-inbox-engine','2023-06-02 07:28:37'),(6,'wp_mail_smtp','2023-06-02 07:28:37'),(7,'wc_update_product_default_cat','2023-06-02 07:28:37'),(8,'woocommerce_payments','2023-06-02 07:28:37'),(9,'wc_update_product_lookup_tables','2023-06-02 07:28:37');
<class 'dbsync.exceptions.DbSyncParseException'> - Confusion, state: 1, token: <Keyword 'CHARAC...' at 0x101F4FAC0>
Index: 6
SQL: CREATE TABLE `tbl_test0` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci NOT NULL,
  `date_created_gmt` datetime DEFAULT '0000-00-00 00:00:00',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;
<class 'dbsync.exceptions.DbSyncParseException'> - Invalid INSERT statement
Index: 4
SQL: INSERT INTO `tbl_test0` VALUES (1,'action-scheduler-migration','2023-06-05 12:11:35'),(2,'wpforms','2023-06-02 07:28:37'),(3,'wc-admin-data','2023-06-02 07:28:37'),(4,'woocommerce-db-updates','2023-06-02 07:28:37'),(5,'woocommerce-remote-inbox-engine','2023-06-02 07:28:37'),(6,'wp_mail_smtp','2023-06-02 07:28:37'),(7,'wc_update_product_default_cat','2023-06-02 07:28:37'),(8,'woocommerce_payments','2023-06-02 07:28:37'),(9,'wc_update_product_lookup_tables','2023-06-02 07:28:37');
Timing:
  Read and split file : 0.00
  Process statements  : 0.01
  Post-Processing     : 0.00
  Compare and output  : 0.00
  Total               : 0.01
(venv) ➜  dbsync git:(main) ✗ 

      ]

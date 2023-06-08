# TODO
## Urgent
* Integration tests - in progress
* Get it to work with dump from MySQL workbench
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
* Summarize diffs to answer questions
* What about tables that don't have a timestamp column? Configure on a table-by-table basis?

LOCK TABLES `staging_tbl_test0` WRITE;
/*!40000 ALTER TABLE `staging_tbl_test0` DISABLE KEYS */;
/*! ALTER TABLE `X` AUTO_INCREMENT=Y */;

/*!40000 ALTER TABLE `staging_tbl_test0` ENABLE KEYS */;
UNLOCK TABLES;


Parsing keys

--
-- Indexes for table `NhU_actionscheduler_logs`
--
ALTER TABLE `NhU_actionscheduler_logs`
  ADD PRIMARY KEY (`log_id`),
  ADD KEY `action_id` (`action_id`),
  ADD KEY `log_date_gmt` (`log_date_gmt`);

--
-- Indexes for table `NhU_ce4wp_abandoned_checkout`
--
ALTER TABLE `NhU_ce4wp_abandoned_checkout`
  ADD PRIMARY KEY (`checkout_id`),
  ADD UNIQUE KEY `checkout_uuid` (`checkout_uuid`);



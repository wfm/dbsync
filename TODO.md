# TODO
## Urgent
* Integration tests - in progress
* Returns 28 rows: select ID,count(\*) from maryjoya_WP5Z2.NhU_posts p group by p.post_date_gmt having count(\*) > 1;
- Weird, ID is the PK
* I've been conflating PK and auto-inc column. They're separate concepts.
* Int columns are stored as strings and converted to int when needed. It's confusing.

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
* Use case-insensitive comparisons

## Future
* Implement stage -> prod
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?
* Prevent SQL injection?
* Generalize the state machine code

# DONE
* Post 1738 was not copied/copied correctly - I think it got a new 
* Safe mode updates
* Do we want to allow updates to PK of tables compared by unique key? I think not...
- For _posts, should we reuse IDs and just update the post date?
- Should we "infill" PKs?
* Add FKs for rest of wc tables
* Review which tables are copied.
* PK errors with synthetic UK
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


The code assumes that a table has one PK column and that column has auto-increment


-- ALTER TABLE `staging_NhU_yoast_indexable_hierarchy`
--   ADD PRIMARY KEY (`indexable_id`,`ancestor_id`),

05:49:59

UPDATE `staging_NhU_wc_admin_note_actions` SET `query`='https://maryjoyart.com/staging/1617/wp-admin/post.php?post=635&action=edit' WHERE `name`='notify-refund-returns-page'	

Error Code: 1175. You are using safe update mode and you tried to update a table without a WHERE that uses a KEY column.  To disable safe mode, toggle the option in Preferences -> SQL Editor and reconnect.

0.00079 sec


ALTER TABLE `NhU_term_relationships`
  ADD PRIMARY KEY (`object_id`,`term_taxonomy_id`),

ALTER TABLE `NhU_wc_category_lookup`
  ADD PRIMARY KEY (`category_tree_id`,`category_id`);

ALTER TABLE `NhU_wc_order_coupon_lookup`
  ADD PRIMARY KEY (`order_id`,`coupon_id`),

ALTER TABLE `NhU_wc_order_tax_lookup`
  ADD PRIMARY KEY (`order_id`,`tax_rate_id`),

ALTER TABLE `NhU_wc_product_attributes_lookup`
  ADD PRIMARY KEY (`product_or_parent_id`,`term_id`,`product_id`,`taxonomy`),

ALTER TABLE `NhU_wc_reserved_stock`
  ADD PRIMARY KEY (`order_id`,`product_id`);

ALTER TABLE `NhU_yoast_indexable_hierarchy`
  ADD PRIMARY KEY (`indexable_id`,`ancestor_id`),

<strong>Your store requires a security update for the WooCommerce Stripe plugin</strong>. Please update the WooCommerce Stripe plugin immediately to address a potential vulnerability.

Error Code: 1062. Duplicate entry '9420' for key 'staging_nhu_postmeta.PRIMARY'

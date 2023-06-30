# Procedure to sync stage to prod:
0. Put sites in maintenance mode (is there a message?)
* Can you stop all the cron jobs? 
- define('DISABLE_WP_CRON', true);
1. Do zip and mysqldump backups and download
2. Do WP Migrate backups of prod and stage
3. Copy media and CSS files from prod to stage using WP Migrate backups
* Install Endurance page cache on stage?
* Don't copy astra-child stuff to stage

4. Run the dbsync program
4. Hand-edit the term_taxonomy updates to keep just the tribe stuff (or make it pessimistic?)
5. Check with Local?
6. Upload the script
7. Run the script
8. Check the stage site
9. Push to prod
10. Check the prod site
11. Turn off maintenance mode

# Procedure to sync staging to prod via Local
0. Export prod and stage from Bluehost using WP-Migrate
0. Import prod into Local (this will change urls from https://maryjoyart.com to https://mary-joy-murphy-prod.local)
0. Disable WP-Cron in Local?
0. Export DB from Local
0. Stop the Local site (this stops the DB too)
0. Combine SQL file in export from Local with export from Staging
0. Run dbsync
0. Migrate files from staging site
0. Start Local, verify correctness
0. Run maint/repair.php. Optimize?
0. Export from local
0. Import into prod

Is there a way to test this with stage?

# TODO
## Urgent
* If syncing with local, change 'https://mary-joy-murphy-prod.local/' to real site URL
* Or maybe not - we need to have it run on local
* Can we stop cron jobs while we sync? define('DISABLE_WP_CRON', true);
* For _options (at least), let DB set the autoinc column
* add FKs for tables we added, _wps_
* Getting warnings that disabling keys is not supported

## Medium-term
* decent test coverage
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
* Why are so many UnpackedInsert objects created for each table?

## Future
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?
* Prevent SQL injection?
* Generalize the state machine code

# DONE
* Implement stage -> prod
* Integration tests - in progress
* There are IDs in the key, value tables that must be updated - in progress
* If we update a value in a k,v table with an ID, do we need to update that?
* Add WC and migrate plugins on both sites 
* are we checking all the tables? i think so
* Can we get a timestamp via a FK?
* Check "maybe insert":
    options - doesn't matter with unique key
* Updates that should really be inserts:
    -- PKs are equal, MAYBE update, MAYBE insert src, distance: 24
    -- Was: {'name': "'Playful Art'", 'slug': "'playful-art'"}
    UPDATE `staging_NhU_terms`
    SET `name`='Market', `slug`='market'
    WHERE `term_id`=49;
* Which tables should be pessimistic? These tables use FK comparisons:
    options - is pessimistic
    term_taxonomy - hand-edit, keep tribe stuff, remove rest
    termmeta - no idea, will make pessimistic
    wc_product_download_directories
* It seems like WP Migrate exports some data that the phpMyAdmin backup misses. This causes our script to be wrong. No, stuff was getting created when the site ran under Local
* Returns 28 rows: select ID,count(\*) from maryjoya_WP5Z2.NhU_posts p group by p.post_date_gmt having count(\*) > 1;
- Weird, ID is the PK
* I've been conflating PK and auto-inc column. They're separate concepts.
* Int columns are stored as strings and converted to int when needed. It's confusing.
* Post 1738 was not copied/copied correctly
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
* filter out data from before 4/7/23 - those records must have been deleted from dst
Trying to merge from stage to prod. There is less data to migrate:
* _options - update any rows?
* _postmeta - many inserts are for test orders which we don't need. Will be reduced if we reduce post inserts
* _posts - records need to be hand-selected
* _term_taxonomy - don't bother updating counts?
* _termmeta - would update 3 records, if it were optimistic. Inserts should be ok
* _terms - a couple of updates should really be inserts
* _usermeta - tempted to skip 
* _wc_admin_note_actions - skip?
* _wc_category_lookup - ok, i think
* _wc_order_product_lookup - skip
* _wc_order_stats - skip
* _wc_order_tax_lookup - skip
* _wc_product_meta_lookup - skip
* _woocommerce_order_itemmeta - skip
* _wps tables - skip these?
* _yoast_indexable - skip
* _yoast_indexable_hierarchy - skip
* _yoast_primary_term - skip
* _yoast_seo_links - skip

===========
2023-06-18

Tables not on the list could be skipped.

===========
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

6/21/23
Is there still something to do with this?
assert old_pk_val < self.dst_table.get_starting_autoinc_val(), "Can't reuse this autoinc value"
* We could wait until we've processed all the records to remap the autoinc values
* Every src AIV that is >= dst starting AIV could be reused.
* Then we'd just have to assign new values to the records being inserted that have:
    src AIV < dst starting AIV


Done:


    # TODO temporary:
    regex = Settings.obj().weak_reference_regex
    items = [
        '_EventVenueID', '_VenueVenueID', '_OrganizerOrganizerID', '_EventOrganizerID',
        'thumbnail_id', 'other-id', 'notanid'
    ]

    for item in items:
        m = regex.search(item)
        print(f"{item} : {m is not None}, {m}")
    return 0


    @staticmethod
    def load_from_file(from_filename: str) -> Self:
        with open(from_filename, "r", encoding="utf8") as file:
            config = json.load(file, )
            settings = Settings(**config)
            return settings

    @staticmethod
    def try_convert_to_enum(x: Any) -> Any:
        if isinstance(x, str) and x.startswith("__enum__"):
            parts = x.split(".")
            enum_type = getattr(S, parts[1])
            value = getattr(enum_type, parts[2])
            print(f"to_enum({x}), value: {value} ({value.name})")
            return value
        return x

    @staticmethod
    def decode_json_hack(item: Any) -> None:
        if hasattr(item, "items"):
            for k, v in item.items():
                item[k] = Settings.decode_json_hack(v)
        elif hasattr(item, "__getitem__"):
            for i in range(len(item)):
                item[i] = Settings.decode_json_hack(item[i])
        else:
            item = Settings.try_convert_to_enum(item)
        return item


0 row(s) affected, 1 warning(s): 1031 Table storage engine for 'NhU_options' doesn't have this option
19:37:14	/*!40000 ALTER TABLE `NhU_options` DISABLE KEYS */	0 row(s) affected, 1 warning(s): 1031 Table storage engine for 'NhU_options' doesn't have this option	0.0010 sec


0 row(s) affected, 1 warning(s): 1031 Table storage engine for 'NhU_options' doesn't have this option

19:37:14	INSERT INTO `NhU_options` (`option_id`, `option_name`, `option_value`, `autoload`) VALUES (96967, 'bh_cdata_retry_count', '8', 'yes'), (96968, 'jetpack_safe_mode_confirmed', '1', 'yes'), (96969, 'jetpack_sync_dedicated_spawn_lock', '1681493577.6842', 'no'), (96970, 'jetpack_sync_error_idc', 'a:7:{s:4:\"home\";s:28:\"maryjoyart.com/staging/1617/\";s:7:\"siteurl\";s:28:\"maryjoyart.com/staging/1617/\";s:10:\"error_code\";s:20:\"jetpack_url_mismatch\";s:15:\"request_siteurl\";s:28:\"maryjoyart.com/staging/1617/\";s:12:\"request_home\";s:28:\"maryjoyart.com/staging/1617/\";s:13:\"wpcom_siteurl\";s:15:\"maryjoyart.com/\";s:10:\"wpcom_home\";s:15:\"maryjoyart.com/\";}', 'yes'), (96971, 'jpsq_sync-1681493551.313020-916049-1', 'a:6:{i:0;s:14:\"updated_option\";i:1;a:3:{i:0;s:15:\"jetpack_options\";i:1;a:14:{s:7:\"version\";s:15:\"12.0:1680673713\";s:11:\"old_version\";s:17:\"11.9.1:1679235985\";s:14:\"last_heartbeat\";i:1681407311;s:2:\"id\";i:215576346;s:6:\"public\";i:1;s:30:\"recommendations_banner_enabled\";b:1;s:27:\"recommendations_conditional\";a:4:{i:0;s:11:\"backup-plan\";i:1;s:5:\"boost\";i:2;s:7:\"protect\";i:3;s:10:\"videopress\";}s:16:\"first_admin_view\";b:1;s:28:\"has_seen_wc_connection_modal\";b:1;s:20:\"recommendations_data\";a:7:{s:16:\"onboardingViewed\";a:0:{}s:23:\"selectedRecommendations\";a:1:{i:0;s:5:\"boost\";}s:22:\"skippedRecommendations\";a:0:{}s:21:\"viewedRecommendations\";a:6:{i:0;s:11:\"backup-plan\";i:1;s:5:\"boost\";i:2;s:7:\"summary\";i:3;s:7:\"protect\";i:4;s:10:\"videopress\";i:5;s:7:\"monitor\";}s:18:\"site-type-personal\";b:0;s:16:\"site-type-agency\";b:0;s:15:\"site-type-store\";b:1;}s:20:\"recommendations_step\";s:16:\"banner-completed\";s:9:\"hide_jitm\";a:5:{s:10:\"videopress\";a:2:{s:14:\"last_dismissal\";i:1678302742;s:6:\"number\";i:1;}s:4:\"scan\";a:2:{s:14:\"last_dismissal\";i:1679068030;s:6:\"number\";i:1;}s:18:\"protect_standalone\";a:2:{s:14:\"last_dismissal\";i:1679169821;s:6:\"number\";i:1;}s:25:\"wooservices-existing-user\";a:2:{s:14:\"last_dismissal\";i:1679689629;s:6:\"number\";i:1;}s:3:\"cdn\";a:2:{s:14:\"last_dismissal\";i:1680026676;s:6:\"number\";i:1;}}s:28:\"fallback_no_verify_ssl_certs\";i:0;s:9:\"time_diff\";i:0;}i:2;a:14:{s:7:\"version\";s:15:\"12.0:1680673713\";s:11:\"old_version\";s:17:\"11.9.1:1679235985\";s:14:\"last_heartbeat\";i:1681493551;s:2:\"id\";i:215576346;s:6:\"public\";i:1;s:30:\"recommendations_banner_enabled\";b:1;s:27:\"recommendations_conditional\";a:4:{i:0;s:11:\"backup-plan\";i:1;s:5:\"boost\";i:2;s:7:\"protect\";i:3;s:10:\"videopress\";}s:16:\"first_admin_view\";b:1;s:28:\"has_seen_wc_connection_modal\";b:1;s:20:\"recommendations_data\";a:7:{s:16:\"onboardingViewed\";a:0:{}s:23:\"selectedRecommendations\";a:1:{i:0;s:5:\"boost\";}s:22:\"skippedRecommendations\";a:0:{}s:21:\"viewedRecommendations\";a:6:{i:0;s:11:\"backup-plan\";i:1;s:5:\"boost\";i:2;s:7:\"summary\";i:3;s:7:\"protect\";i:4;s:10:\"videopress\";i:5;s:7:\"monitor\";}s:18:\"site-type-personal\";b:0;s:16:\"site-type-agency\";b:0;s:15:\"site-type-store\";b:1;}s:20:\"recommendations_step\";s:16:\"banner-completed\";s:9:\"hide_jitm\";a:5:{s:10:\"videopress\";a:2:{s:14:\"last_dismissal\";i:1678302742;s:6:\"number\";i:1;}s:4:\"scan\";a:2:{s:14:\"last_dismissal\";i:1679068030;s:6:\"number\";i:1;}s:18:\"protect_standalone\";a:2:{s:14:\"last_dismissal\";i:1679169821;s:6:\"number\";i:1;}s:25:\"wooservices-existing-user\";a:2:{s:14:\"last_dismissal\";i:1679689629;s:6:\"number\";i:1;}s:3:\"cdn\";a:2:{s:14:\"last_dismissal\";i:1680026676;s:6:\"number\";i:1;}}s:28:\"fallback_no_verify_ssl_certs\";i:0;s:9:\"time_diff\";i:0;}}i:2;i:0;i:3;d:1681493551.3116691112518310546875;i:4;b:0;i:5;a:14:{s:13:\"wpcom_user_id\";N;s:16:\"external_user_id\";i:0;s:12:\"display_name\";N;s:10:\"user_email\";N;s:10:\"user_roles\";a:0:{}s:15:\"translated_role\";N;s:7:\"is_cron\";b:1;s:7:\"is_rest\";b:0;s:9:\"is_xmlrpc\";b:0;s:10:\"is_wp_rest\";b:0;s:7:\"is_ajax\";b:0;s:11:\"is_wp_admin\";b:0;s:6:\"is_cli\";b:0;s:8:\"from_url\";s:95:\"https://maryjoyart.com/wp-cron.php?doing_wp_cron=1681493549.4250431060791015625000\";}}', ...	

Error Code: 1062. Duplicate entry '96967' for key 'PRIMARY'	0.00055 sec


16:59:11	update term_taxonomy set parent = 57 where term_id = 33 or term_id = 45	Error Code: 1146. Unknown error 1146	0.00042 sec

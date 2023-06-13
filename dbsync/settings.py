"""Configuration-related stuffs"""

import re
from typing import Dict, List, Any
from pydantic import BaseModel, PrivateAttr
from enum import Enum

from dbsync.exceptions import DbSyncParseException


def to_camel(string: str) -> str:
    # from the pydantic docs:
    # return ''.join(word.capitalize() for word in string.split('_'))
    # I prefer LCC:
    words = string.split("_")
    first = words.pop(0)
    rest = "".join(word.capitalize() for word in words)
    return first + rest


class DmlOptions(Enum):
    DISABLE_AUTO_INCREMENT = 1  # with ALTER TABLE statements
    GENERATE_LOCK_TABLES = 2    # lock tables, disable keys, set auto-inc value


class Settings(BaseModel, allow_mutation=True, alias_generator=to_camel):
    #
    # In Bluehost's staging scheme, the prod tables
    # are copied to tables with the prefix "staging_"
    # To keep things simple, we'll always update the
    # "staging" tables from the prod tables.
    #
    # By default, all tables whose names begin with <src_prefix>
    # are compared to the tables whose names begin with <dst_prefix>.
    # If you specify included_tables, only those tables are looked at.
    # The name should be the name without any prefix.
    # If you specify excluded_tables, all tables except those
    # are looked at.
    # If a table name is in both lists, it will be excluded.
    # The defaults are for maryjoyart.com
    db_name: str = "maryjoya_WP5Z2"
    # Tables are named like <src_prefix><tbl_prefix><name>
    src_prefix: str = ""
    dst_prefix: str = "staging_"
    tbl_prefix: str = "NhU_"
    included_tables: List[str] = []
    excluded_tables: List[str] = [
        # "actionscheduler_actions",
        # "actionscheduler_claims",
        # "NhU_actionscheduler_groups",
        # "actionscheduler_logs",
        # "options"
    ]

    timestamp_cols: Dict[str, List[str]] = {
        "actionscheduler_actions": ["scheduled_date_gmt"],
        "actionscheduler_claims": ["date_created_gmt"],
        "actionscheduler_logs": ["log_date_gmt"],
        "ce4wp_abandoned_checkout": [
            "checkout_recovered", "checkout_updated", "checkout_created"],
        "comments": ["comment_date_gmt"],
        "e_events": ["created_at"],
        "links": ["link_updated"],
        "lockdowns": ["release_date", "lockdown_date"],
        "login_fails": ["login_attempt_date"],
        "nfd_data_event_queue": ["created_at"],
        "posts": ["post_modified_gmt", "post_date_gmt"],
        "sib_model_users": ["user_added_date"],
        "tec_events": ["updated_at"],
        "tec_occurrences": ["updated_at"],
        "users": ["user_registered"],
        "wc_admin_notes": ["date_created"],
        "wc_customer_lookup": ["date_last_active", "date_registered"],
        "wc_download_log": ["timestamp"],
        "wc_order_coupon_lookup": ["date_created"],
        "wc_order_product_lookup": ["date_created"],
        "wc_order_stats": ["date_completed", "date_paid", "date_created"],
        "wc_order_tax_lookup": ["date_created"],
        "wc_reserved_stock": ["timestamp"],
        "wc_webhooks": ["date_modified_gmt", "date_created_gmt"],
        "woocommerce_downloadable_product_permissions": ["access_granted"],
        "woocommerce_log": ["timestamp"],
        "wpforms_logs": ["create_at"],
        "wpforms_tasks_meta": ["date"],
        "wpmailsmtp_debug_events": ["created_at"],
        "wpmailsmtp_tasks_meta": ["date"],
        "yoast_indexable": ["updated_at", "created_at"],
        "yoast_primary_term": ["updated_at", "created_at"]
    }

    # idea: use the auto_inc values from the time the
    # stage site was created as a guide.
    # Data is from 3/24/23
    high_water_marks = {
        'NhU_actionscheduler_groups': 9,
        'NhU_ce4wp_abandoned_checkout': 0,
        'NhU_ce4wp_contacts': 0,
        'NhU_commentmeta': 0,
        'NhU_comments': 14,
        'NhU_e_events': 0,
        'NhU_links': 0,
        'NhU_postmeta': 7359,
        'NhU_posts': 1434,
        'NhU_sib_model_forms': 2,
        'NhU_sib_model_users': 0,
        'NhU_tec_events': 5,
        'NhU_tec_occurrences': 5,
        'NhU_termmeta': 18,
        'NhU_terms': 47,
        'NhU_term_relationships': -1,
        'NhU_term_taxonomy': 47,
        'NhU_usermeta': 199,
        'NhU_users': 3,
        'NhU_wc_admin_notes': 51,
        'NhU_wc_admin_note_actions': 2278,
        'NhU_wc_category_lookup': -1,
        'NhU_wc_customer_lookup': 2,
        'NhU_wc_download_log': 0,
        'NhU_wc_order_coupon_lookup': -1,
        'NhU_wc_order_product_lookup': -1,
        'NhU_wc_order_stats': -1,
        'NhU_wc_order_tax_lookup': -1,
        'NhU_wc_product_attributes_lookup': -1,
        'NhU_wc_product_download_directories': 3,
        'NhU_wc_product_meta_lookup': -1,
        'NhU_wc_rate_limits': 0,
        'NhU_wc_reserved_stock': -1,
        'NhU_wc_tax_rate_classes': 0,
        'NhU_wc_webhooks': 0,
        'NhU_woocommerce_api_keys': 0,
        'NhU_woocommerce_attribute_taxonomies': 2,
        'NhU_woocommerce_downloadable_product_permissions': 0,
        'NhU_woocommerce_log': 0,
        'NhU_woocommerce_order_itemmeta': 44,
        'NhU_woocommerce_order_items': 7,
        'NhU_woocommerce_payment_tokenmeta': 0,
        'NhU_woocommerce_payment_tokens': 0,
        'NhU_woocommerce_sessions': 567,
        'NhU_woocommerce_shipping_zones': 3,
        'NhU_woocommerce_shipping_zone_locations': 12,
        'NhU_woocommerce_shipping_zone_methods': 6,
        'NhU_woocommerce_tax_rates': 2,
        'NhU_woocommerce_tax_rate_locations': 3,
        'NhU_wpforms_tasks_meta': 23,
        'NhU_wpmailsmtp_debug_events': 3,
        'NhU_wpmailsmtp_tasks_meta': 0,
        'NhU_yoast_indexable': 416,
        'NhU_yoast_indexable_hierarchy': -1,
        'NhU_yoast_migrations': 24,
        'NhU_yoast_primary_term': 8,
        'NhU_yoast_seo_links': 2190
    }

    # Controls what happens when data for a pair of
    # tables differ, but the tables don't have
    # a timestamp column
    update_tables_without_timestamp: bool = False

    # Override the above
    update_specific_tables_without_timestamp: Dict[str, bool] = {
        "options": False
    }

    integer_types = [
        "INTEGER", "INT", "SMALLINT", "TINYINT", "MEDIUMINT", "BIGINT"
    ]
    numeric_types = [
        "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL", "DEC", "FIXED",
    ]

    # filename for generated sql, or None for stdout
    output_file: str | None = "output.sql"
    # if not None, generated sql is written here instead
    # of filename above. Shoud be of type TextIOWrapper
    file_descriptor: Any | None = None

    verbose_mode: bool = False

    dml_options: DmlOptions = DmlOptions.GENERATE_LOCK_TABLES

    _table_name_regex: re = PrivateAttr()
    _integer_types_regex: re = PrivateAttr()
    _numeric_types_regex: re = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self.init()

    def init(self):
        pattern = f"^`?({self.src_prefix}|{self.dst_prefix}){self.tbl_prefix}(.+?)`?$"
        self._table_name_regex = re.compile(pattern, flags=re.IGNORECASE)
        self._integer_types_regex = \
            re.compile(f"^({'|'.join(self.integer_types)})", flags=re.IGNORECASE)
        self._numeric_types_regex = \
            re.compile(f"^({'|'.join(self.numeric_types)})", flags=re.IGNORECASE)

    def is_integer_datatype(self, datatype):
        return self._integer_types_regex.search(datatype) is not None

    def is_numeric_datatype(self, datatype):
        return self._numeric_types_regex.search(datatype) is not None

    def get_base_table_name(self, table_name: str) -> str | None:
        """Strips the prefixes from the table name"""
        m = self._table_name_regex.search(table_name)
        if m:
            return m.group(2)

        print("=" * 20)
        print(repr(self._table_name_regex))
        print(repr(m))
        msg = f"Doesn't follow table name conventions: {table_name}"
        raise DbSyncParseException(msg)

    def get_src_table_name(self, table_name: str) -> str:
        base_name = self.get_base_table_name(table_name)
        return f"{self.src_prefix}{self.tbl_prefix}{base_name}"

    def should_include_table(self, table_name):
        """
        Returns true if the table is included and not excluded
        based on the included_tables and excluded_tables lists.
        """
        base_name = self.get_base_table_name(table_name)
        include = len(self.included_tables) == 0 or \
            base_name in self.included_tables
        exclude = base_name in self.excluded_tables
        return include and not exclude

    def table_has_timestamp(self, table_name: str) -> bool:
        base_name = self.get_base_table_name(table_name)
        return base_name in self.timestamp_cols

    def should_update_table(self, table_name: str) -> bool:
        base_name = self.get_base_table_name(table_name)
        result = self.update_specific_tables_without_timestamp.get(base_name)
        if result is None:
            result = self.update_tables_without_timestamp
        return result

    def get_timestamp_cols(self, table_name):
        """
        Returns the timestamp columns in a table, in the order
        in which they should be evaluated. Returns an empty
        list if there are no timestamp columns in the table.
        """
        base_name = self.get_base_table_name(table_name)
        if base_name in self.timestamp_cols:
            return self.timestamp_cols[base_name]
        return []

    def get_high_water(self, table_name) -> int:
        """
        Returns the auto_inc value from an earlier backup
        of the database. Returns -1 if there
        is no information.
        """
        if table_name in self.high_water_marks:
            return self.high_water_marks[table_name]
        return -1

    @classmethod
    def obj(cls, initial_settings=None):
        global _global_config

        if _global_config is None:
            if initial_settings is None:
                _global_config = cls()
            else:
                _global_config = initial_settings
            _global_config.init()
        elif initial_settings is not None:
            msg = "You missed your chance to initialize the settings"
            raise DbSyncParseException(msg)

        return _global_config


_global_config: Settings | None = None

#
# From https://wp-staging.com/docs/the-wordpress-database-structure/
# List of WordPress Core Tables
# wp_options
# wp_users,
# wp_usermeta
# wp_posts
# wp_postmeta
# wp_terms
# wp_term_relationships
# wp_term_taxonomy
# wp_comments
# wp_commentmeta
# wp_links
#
# Woocommerce tables can be found here:
# https://github.com/woocommerce/woocommerce/wiki/Database-Description
#
# All tables in the maryjoyart database (as of 2023-05-26):
# `NhU_actionscheduler_actions,
# `NhU_actionscheduler_claims,
# `NhU_actionscheduler_groups,
# `NhU_actionscheduler_logs,
# `NhU_ce4wp_abandoned_checkout,
# `NhU_ce4wp_contacts,
# `NhU_commentmeta,
# `NhU_comments,
# `NhU_e_events,
# `NhU_links,
# `NhU_lockdowns,
# `NhU_login_fails,
# `NhU_nfd_data_event_queue,
# `NhU_options,
# `NhU_postmeta,
# `NhU_posts,
# `NhU_sib_model_forms,
# `NhU_sib_model_users,
# `NhU_tec_events,
# `NhU_tec_occurrences,
# `NhU_termmeta,
# `NhU_terms,
# `NhU_term_relationships,
# `NhU_term_taxonomy,
# `NhU_usermeta,
# `NhU_users,
# `NhU_wc_admin_notes,
# `NhU_wc_admin_note_actions,
# `NhU_wc_category_lookup,
# `NhU_wc_customer_lookup,
# `NhU_wc_download_log,
# `NhU_wc_order_coupon_lookup,
# `NhU_wc_order_product_lookup,
# `NhU_wc_order_stats,
# `NhU_wc_order_tax_lookup,
# `NhU_wc_product_attributes_lookup,
# `NhU_wc_product_download_directories,
# `NhU_wc_product_meta_lookup,
# `NhU_wc_rate_limits,
# `NhU_wc_reserved_stock,
# `NhU_wc_tax_rate_classes,
# `NhU_wc_webhooks,
# `NhU_woocommerce_api_keys,
# `NhU_woocommerce_attribute_taxonomies,
# `NhU_woocommerce_downloadable_product_permissions,
# `NhU_woocommerce_log,
# `NhU_woocommerce_order_itemmeta,
# `NhU_woocommerce_order_items,
# `NhU_woocommerce_payment_tokenmeta,
# `NhU_woocommerce_payment_tokens,
# `NhU_woocommerce_sessions,
# `NhU_woocommerce_shipping_zones,
# `NhU_woocommerce_shipping_zone_locations,
# `NhU_woocommerce_shipping_zone_methods,
# `NhU_woocommerce_tax_rates,
# `NhU_woocommerce_tax_rate_locations,
# `NhU_wpforms_logs,
# `NhU_wpforms_tasks_meta,
# `NhU_wpmailsmtp_debug_events,
# `NhU_wpmailsmtp_tasks_meta,
# `NhU_yoast_indexable,
# `NhU_yoast_indexable_hierarchy,
# `NhU_yoast_migrations,
# `NhU_yoast_primary_term,
# `NhU_yoast_seo_links,

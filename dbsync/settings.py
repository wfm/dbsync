"""Configuration-related stuffs"""

import re
from typing import List
from pydantic import BaseModel, PrivateAttr

from dbsync.exceptions import DbSyncParseException


def to_camel(string: str) -> str:
    # from the pydantic docs:
    # return ''.join(word.capitalize() for word in string.split('_'))
    # I prefer LCC:
    words = string.split("_")
    first = words.pop(0)
    rest = "".join(word.capitalize() for word in words)
    return first + rest


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
    save_included_tables: List[str] = [
        "options",
        "users",
        "usermeta",
        "posts",
        "postmeta",
        "terms",
        "term_relationships",
        "term_taxonomy",
        "comments",
        "commentmeta",
        "links",
        "ce4wp_abandoned_checkout",
        "ce4wp_contacts",
        "sib_model_forms",
        "sib_model_users",
        "tec_events",
        "tec_occurrences",
        "wc_admin_notes",
        "wc_admin_note_actions",
        "wc_category_lookup",
        "wc_customer_lookup",
        "wc_download_log",
        "wc_order_coupon_lookup",
        "wc_order_product_lookup",
        "wc_order_stats",
        "wc_order_tax_lookup",
        "wc_product_attributes_lookup",
        "wc_product_download_directories",
        "wc_product_meta_lookup",
        "wc_rate_limits",
        "wc_reserved_stock",
        "wc_tax_rate_classes",
        "wc_webhooks",
        "woocommerce_api_keys",
        "woocommerce_attribute_taxonomies",
        "woocommerce_downloadable_product_permissions",
        "woocommerce_log",
        "woocommerce_order_itemmeta",
        "woocommerce_order_items",
        "woocommerce_payment_tokenmeta",
        "woocommerce_payment_tokens",
        "woocommerce_sessions",
        "woocommerce_shipping_zones",
        "woocommerce_shipping_zone_locations",
        "woocommerce_shipping_zone_methods",
        "woocommerce_tax_rates",
        "woocommerce_tax_rate_locations",
        "wpforms_tasks_meta",
        "yoast_indexable",
        "yoast_indexable_hierarchy",
        "yoast_migrations",
        "yoast_primary_term",
        "yoast_seo_links"
    ]
    excluded_tables: List[str] = []

    # filename for generated sql, or None for stdout
    output_file: str | None = "output.sql"

    _table_name_regex: re = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self.init()

    def init(self):
        pattern = f"^`?({self.src_prefix}|{self.dst_prefix}){self.tbl_prefix}(.+?)`?$"
        self._table_name_regex = re.compile(pattern, flags=re.IGNORECASE)

    def get_base_table_name(self, table_name: str) -> str | None:
        """Strips the prefixes from the table name"""
        m = self._table_name_regex.search(table_name)
        if m:
            return m.group(2)

        print("="*20)
        print(repr(self._table_name_regex))
        print(repr(m))
        msg = f"Doesn't follow table name conventions: {table_name}"
        raise DbSyncParseException(msg)

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

    @classmethod
    def obj(cls, initial_settings=None):
        # TODO read this from a file
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

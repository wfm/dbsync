"""Configuration-related stuffs"""

from dataclasses import dataclass, field
import re
import types
from typing import Callable, Dict, List, Any, Self, Tuple
from pydantic import BaseModel, PrivateAttr
from enum import Enum

import dbsync.settings as S
from dbsync.exceptions import DbSyncParseException


def to_camel(string: str) -> str:
    # from the pydantic docs:
    # return ''.join(word.capitalize() for word in string.split('_'))
    # I prefer LCC:
    words = string.split("_")
    first = words.pop(0)
    rest = "".join(word.capitalize() for word in words)
    return first + rest


# methods for "special rules" for modding src data
def alter_table_name(value: str) -> str:
    settings = Settings.obj()
    pattern = settings.get_test_table_name_pattern()
    repl = f"{settings.dst_prefix}{settings.tbl_prefix}"
    return re.sub(pattern, repl, value)


def alter_site_url(value: str) -> str:
    settings = Settings.obj()
    pattern = settings.get_test_site_url_pattern()
    repl = settings.get_test_site_url_replacement()
    return re.sub(pattern, repl, value)


class DmlOptions(str, Enum):
    DISABLE_AUTO_INCREMENT = "disable_auto_increment"     # with ALTER TABLE statements
    GENERATE_LOCK_TABLES = "generate_lock_tables"         # lock tables, disable keys, set auto-inc


class SyncActions(str, Enum):
    DEFAULT = "default"
    SKIP = "skip"
    COPY = "copy"
    MERGE = "merge"


class UpdateModes(str, Enum):
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"


class UpdateActions(str, Enum):
    COPY_SRC = "copy_src"
    KEEP_DST = "keep_dst"
    INSERT_SRC = "insert_src"
    DO_NOTHING = "do_nothing"
    DEFAULT = "default"
    SKIP = "skip"


@dataclass
class ForeignKey:
    src_table: str
    src_column: str
    dst_table: str
    dst_column: str
    # A "weak reference" may refer to another table or may just have data
    # The src table will be a key,value store
    weak: bool = field(default=False)
    key_column: str = field(default_factory=str)


# TODO Switch to this?
@dataclass
class TableOptions:
    action: SyncActions
    use_time_based_comparison: bool
    timestamp_cols: List[str] | None
    update_without_timestamp: bool | None
    highwater_mark: int
    foreign_keys: List[ForeignKey]
    synthetic_unique_key: List[str] = field(default_factory=list)
    special_rules: Dict[str, Callable[[str], str]] = field(default_factory=dict)


class Settings(BaseModel):
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
    # Bluehost changes the URLs in the content to point to the staging site
    base_uri: str = "https://maryjoyart.com"
    src_uri_path: str = ""
    dst_uri_path: str = "/staging/1617"

    included_tables: List[str] = []
    excluded_tables: List[str] = []

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
    # I must not be using this data right.
    # Data is from 3/24/23, staging site was created 4/7/23, i think
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

    foreign_keys: List[ForeignKey] = [
        ForeignKey("actionscheduler_actions", "group_id", "actionscheduler_groups", "group_id"),
        ForeignKey("actionscheduler_actions", "claim_id", "actionscheduler_claims", "claim_id"),
        ForeignKey("actionscheduler_logs", "action_id", "actionscheduler_actions", "action_id"),
        ForeignKey("ce4wp_abandoned_checkout", "user_id", "users", "ID"),
        ForeignKey("commentmeta", "comment_id", "comments", "comment_ID"),
        ForeignKey("commentmeta", "meta_value", "posts", "ID", weak=True, key_column="meta_key"),
        ForeignKey("comments", "comment_post_ID", "posts", "ID"),
        ForeignKey("comments", "comment_parent", "comments", "comment_ID"),
        ForeignKey("comments", "user_id", "users", "ID"),
        ForeignKey("links", "link_owner", "users", "ID"),
        ForeignKey("lockdowns", "user_id", "users", "ID"),
        ForeignKey("login_fails", "user_id", "users", "ID"),
        ForeignKey("options", "option_value", "posts", "ID", weak=True, key_column="option_name"),
        ForeignKey("postmeta", "post_id", "posts", "ID"),
        ForeignKey("postmeta", "meta_value", "posts", "ID", weak=True, key_column="meta_key"),
        ForeignKey("posts", "post_author", "users", "ID"),
        ForeignKey("posts", "post_parent", "posts", "ID"),
        ForeignKey("tec_events", "post_id", "posts", "ID"),
        ForeignKey("tec_occurrences", "event_id", "tec_events", "event_id"),
        ForeignKey("tec_occurrences", "post_id", "posts", "ID"),
        ForeignKey("termmeta", "term_id", "terms", "term_id"),
        ForeignKey("termmeta", "meta_value", "posts", "ID", weak=True, key_column="meta_key"),
        # Not sure how to handle this, since it can refer to many tables.
        # It mostly refers to the posts table, so we'll run with that.
        ForeignKey("term_relationships", "object_id", "posts", "ID"),
        ForeignKey("term_relationships", "term_taxonomy_id", "term_taxonomy", "term_taxonomy_id"),
        ForeignKey("term_taxonomy", "term_id", "terms", "term_id"),
        ForeignKey("term_taxonomy", "parent", "term_taxonomy", "term_taxonomy_id"),
        ForeignKey("usermeta", "user_id", "users", "ID"),
        ForeignKey("usermeta", "meta_value", "posts", "ID", weak=True, key_column="meta_key"),
        # Only some of the Woocommerce tables are documented
        # See: https://github.com/woocommerce/woocommerce/wiki/Database-Description
        # I guessed at the others
        ForeignKey(
            "wc_download_log", "permission_id",
            "woocommerce_downloadable_product_permissions", "permission_id"),
        ForeignKey("wc_download_log", "user_id", "users", "ID"),
        ForeignKey("wc_webhooks", "user_id", "users", "ID"),

        ForeignKey("wc_admin_note_actions", "note_id", "wc_admin_notes", "note_id"),
        ForeignKey("wc_customer_lookup", "user_id", "users", "ID"),
        ForeignKey("wc_order_coupon_lookup", "order_id", "posts", "ID"),
        ForeignKey("wc_order_product_lookup", "order_id", "posts", "ID"),
        ForeignKey("wc_order_product_lookup", "product_id", "posts", "ID"),
        ForeignKey("wc_order_product_lookup", "customer_id", "wc_customer_lookup", "customer_id"),
        ForeignKey("wc_order_stats", "order_id", "posts", "ID"),
        ForeignKey("wc_order_stats", "parent_id", "wc_order_stats", "order_id"),
        ForeignKey("wc_order_stats", "customer_id", "wc_customer_lookup", "customer_id"),
        ForeignKey("wc_order_tax_lookup", "order_id", "posts", "ID"),
        ForeignKey("wc_order_tax_lookup", "tax_rate_id", "woocommerce_tax_rates", "tax_rate_id"),
        ForeignKey("wc_product_attributes_lookup", "product_id", "posts", "ID"),
        ForeignKey("wc_product_attributes_lookup", "product_or_parent_id", "posts", "ID"),
        ForeignKey("wc_product_attributes_lookup", "term_id", "terms", "term_id"),
        ForeignKey("wc_product_meta_lookup", "product_id", "posts", "ID"),
        ForeignKey("wc_reserved_stock", "order_id", "posts", "ID"),
        ForeignKey("wc_reserved_stock", "product_id", "posts", "ID"),

        ForeignKey("woocommerce_api_keys", "user_id", "users", "ID"),
        ForeignKey("woocommerce_downloadable_product_permissions", "product_id", "posts", "ID"),
        ForeignKey("woocommerce_downloadable_product_permissions", "order_id", "posts", "ID"),
        ForeignKey("woocommerce_downloadable_product_permissions", "user_id", "users", "ID"),
        ForeignKey(
            "woocommerce_order_itemmeta", "order_item_id",
            "woocommerce_order_items", "order_item_id"),
        ForeignKey("woocommerce_order_items", "order_id", "posts", "ID"),
        ForeignKey(
            "woocommerce_payment_tokenmeta", "payment_token_id",
            "woocommerce_payment_tokens", "token_id"),
        ForeignKey("woocommerce_payment_tokens", "user_id", "users", "ID"),
        ForeignKey("wc_product_meta_lookup", "product_id", "posts", "ID"),
        ForeignKey(
            "woocommerce_shipping_zone_locations", "zone_id",
            "woocommerce_shipping_zones", "zone_id"),
        ForeignKey(
            "woocommerce_shipping_zone_methods", "zone_id",
            "woocommerce_shipping_zones", "zone_id"),
        ForeignKey(
            "woocommerce_tax_rate_locations", "tax_rate_id",
            "woocommerce_tax_rates", "tax_rate_id"),
        # I left out wpforms_ tables for now
        ForeignKey("yoast_indexable", "object_id", "posts", "ID"),
        ForeignKey("yoast_indexable", "author_id", "users", "ID"),
        ForeignKey("yoast_indexable", "post_parent", "posts", "ID"),
        ForeignKey("yoast_primary_term", "post_id", "posts", "ID"),
        ForeignKey("yoast_primary_term", "term_id", "terms", "term_id"),
        ForeignKey("yoast_seo_links", "post_id", "posts", "ID"),
        ForeignKey("yoast_seo_links", "target_post_id", "posts", "ID"),
    ]

    # TODO fill this out with the TableOptions class above
    table_options = {
        "actionscheduler_actions": {"action": SyncActions.COPY},
        "actionscheduler_claims": {"action": SyncActions.MERGE},
        "actionscheduler_groups": {"action": SyncActions.MERGE},
        "actionscheduler_logs": {"action": SyncActions.COPY},
        "ce4wp_abandoned_checkout": {"action": SyncActions.MERGE},
        "ce4wp_contacts": {"action": SyncActions.MERGE},
        "commentmeta": {"action": SyncActions.MERGE},
        "comments": {"action": SyncActions.MERGE},
        "e_events": {"action": SyncActions.MERGE},
        "links": {"action": SyncActions.MERGE},
        "lockdowns": {"action": SyncActions.MERGE},
        "login_fails": {"action": SyncActions.MERGE},
        "nfd_data_event_queue": {"action": SyncActions.MERGE},
        "options": {
            "action": SyncActions.MERGE,
            "update_mode": UpdateModes.PESSIMISTIC,
            "special_rules": {
                "option_name": alter_table_name,
                "option_value": alter_site_url
            }
        },
        "postmeta": {
            "action": SyncActions.MERGE,
            "synthetic_unique_key": ["post_id", "meta_key"]
        },
        "posts": {
            "action": SyncActions.MERGE,
            "use_time_based_comparison": True,
            "special_rules": {
                "guid": alter_site_url,
                "post_content": alter_site_url
            }
        },
        "sib_model_forms": {"action": SyncActions.MERGE},
        "sib_model_users": {"action": SyncActions.MERGE},
        "tec_events": {"action": SyncActions.MERGE},
        "tec_occurrences": {"action": SyncActions.MERGE},
        "termmeta": {
            "action": SyncActions.MERGE,
            "update_mode": UpdateModes.PESSIMISTIC,
        },
        "terms": {
            "action": SyncActions.MERGE,
            "row_level_actions": [
                ([49], UpdateActions.INSERT_SRC)    # TODO tuple not preserved through json round-trip
            ]
        },
        "term_relationships": {"action": SyncActions.MERGE},
        "term_taxonomy": {"action": SyncActions.MERGE},
        "usermeta": {
            "action": SyncActions.MERGE,
            "synthetic_unique_key": ["user_id", "meta_key"],
            "special_rules": {
                "meta_key": alter_table_name,
                "meta_value": alter_table_name
            }
        },
        "users": {"action": SyncActions.MERGE},
        "wc_admin_notes": {
            "action": SyncActions.MERGE,
            "synthetic_unique_key": ["name"]
        },
        "wc_admin_note_actions": {
            "action": SyncActions.MERGE,
            "synthetic_unique_key": ["name"],
            "special_rules": {
                "query": alter_site_url
            }
        },
        "wc_category_lookup": {"action": SyncActions.MERGE},
        "wc_customer_lookup": {"action": SyncActions.MERGE},        # was COPY
        "wc_download_log": {"action": SyncActions.MERGE},
        "wc_order_coupon_lookup": {"action": SyncActions.MERGE},
        "wc_order_product_lookup": {"action": SyncActions.MERGE},
        "wc_order_stats": {"action": SyncActions.MERGE},
        "wc_order_tax_lookup": {"action": SyncActions.MERGE},
        "wc_product_attributes_lookup": {"action": SyncActions.MERGE},
        "wc_product_download_directories": {
            "action": SyncActions.MERGE,
            "special_rules": {
                "url": alter_site_url
            }
        },
        "wc_product_meta_lookup": {"action": SyncActions.MERGE},
        "wc_rate_limits": {"action": SyncActions.MERGE},
        "wc_reserved_stock": {"action": SyncActions.MERGE},
        "wc_tax_rate_classes": {"action": SyncActions.MERGE},
        "wc_webhooks": {"action": SyncActions.MERGE},
        "woocommerce_api_keys": {"action": SyncActions.MERGE},
        "woocommerce_attribute_taxonomies": {"action": SyncActions.MERGE},
        "woocommerce_downloadable_product_permissions": {"action": SyncActions.MERGE},
        "woocommerce_log": {"action": SyncActions.MERGE},
        "woocommerce_order_itemmeta": {"action": SyncActions.MERGE},
        "woocommerce_order_items": {"action": SyncActions.MERGE},
        "woocommerce_payment_tokenmeta": {"action": SyncActions.MERGE},
        "woocommerce_payment_tokens": {"action": SyncActions.MERGE},
        "woocommerce_sessions": {"action": SyncActions.COPY},
        "woocommerce_shipping_zones": {"action": SyncActions.MERGE},
        "woocommerce_shipping_zone_locations": {"action": SyncActions.MERGE},
        "woocommerce_shipping_zone_methods": {"action": SyncActions.MERGE},
        "woocommerce_tax_rates": {"action": SyncActions.MERGE},
        "woocommerce_tax_rate_locations": {"action": SyncActions.MERGE},
        "wpforms_logs": {"action": SyncActions.MERGE},
        "wpforms_payment_meta": {"action": SyncActions.MERGE},
        "wpforms_payments": {"action": SyncActions.MERGE},
        "wpforms_tasks_meta": {"action": SyncActions.MERGE},
        "wpmailsmtp_debug_events": {"action": SyncActions.MERGE},
        "wpmailsmtp_tasks_meta": {"action": SyncActions.MERGE},
        "yoast_indexable": {
            "action": SyncActions.MERGE,
            "special_rules": {
                "open_graph_image": alter_site_url,
                "open_graph_image_meta": alter_site_url,
                "permalink": alter_site_url,
                "twitter_image": alter_site_url,
            }
        },
        "yoast_indexable_hierarchy": {
            "action": SyncActions.MERGE,
            "synthetic_primary_key": ["indexable_id"]
        },
        "yoast_migrations": {"action": SyncActions.MERGE},
        "yoast_primary_term": {"action": SyncActions.MERGE},
        "yoast_seo_links": {
            "action": SyncActions.MERGE,
            "special_rules": {
                "url": alter_site_url
            }
        }
    }

    default_sync_action: SyncActions = SyncActions.DEFAULT
    default_update_mode: UpdateModes = UpdateModes.OPTIMISTIC
    # if True, don't output anything for the pessimistically omitted statements
    # Otherwise, generate commented-out code
    omit_pessimistic_sql: bool = True

    # Controls what happens when data for a pair of
    # tables differ, but the tables don't have
    # a timestamp column
    update_tables_without_timestamp: bool = True

    # Override the above
    update_specific_tables_without_timestamp: Dict[str, bool] = {
        "usermeta": True
    }

    integer_types = [
        "INTEGER", "INT", "SMALLINT", "TINYINT", "MEDIUMINT", "BIGINT"
    ]
    numeric_types = [
        "DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL", "DEC", "FIXED",
    ]

    # filename for generated sql, or None for stdout
    output_file: str | None = "./output/output.sql"
    # if not None, generated sql is written here instead
    # of filename above. Shoud be of type TextIOWrapper
    file_descriptor: Any | None = None

    # prints to stdout if true:
    verbose_mode: bool = False
    # prints more stuff if true
    debug_mode: bool = False

    # don't copy tables if true. used when "verifying" previous run:
    verify_mode: bool = False

    dml_options: DmlOptions = DmlOptions.GENERATE_LOCK_TABLES

    _table_name_regex: re = PrivateAttr()
    _integer_types_regex: re = PrivateAttr()
    _numeric_types_regex: re = PrivateAttr()
    _weak_reference_regex: re = PrivateAttr()

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

        self._weak_reference_regex = \
            re.compile(r"^(['\"])(.+[\-_]id|_.*(Event|Venue|Organizer).*ID)\1$")

        # if we are rehydrating from json, add function references in the special rules
        for opt in self.table_options.values():
            if "special_rules" in opt:
                sr = opt["special_rules"]
                for key in sr:
                    if isinstance(sr[key], str):
                        sr[key] = getattr(S, sr[key])

    @property
    def weak_reference_regex(self) -> re:
        return self._weak_reference_regex

    def get_test_table_name_pattern(self) -> str:
        if len(self.src_prefix) == 0:
            return f"(?<!{self.dst_prefix}){self.tbl_prefix}"
        return f"{self.src_prefix}{self.tbl_prefix}"

    def get_test_site_url_pattern(self) -> str:
        assert len(self.src_uri_path) > 0 or len(self.dst_uri_path), \
            "Assumption: staging url path is different from prod"
        if len(self.src_uri_path) == 0:
            return r"\b" + self.base_uri + f"(?!{self.dst_uri_path})"

        return r"\b" + self.base_uri + self.src_uri_path

    def get_test_site_url_replacement(self) -> str:
        return self.base_uri + self.dst_uri_path

    def get_test_patterns(self) -> List[re.Pattern]:
        result = [
            re.compile(self.get_test_table_name_pattern()),
            re.compile(self.get_test_site_url_pattern())
        ]
        return result

    def is_integer_datatype(self, datatype):
        return self._integer_types_regex.search(datatype) is not None

    def is_numeric_datatype(self, datatype):
        return self._numeric_types_regex.search(datatype) is not None

    def get_base_table_name(self, table_name: str) -> str | None:
        """Strips the prefixes from the table name"""
        m = self._table_name_regex.search(table_name)
        if m:
            return m.group(2)
        msg = f"Doesn't follow table name conventions: {table_name}"
        raise DbSyncParseException(msg)

    def patch_table_name(self, from_base: str, from_name: str):
        pattern = f"^(({self.src_prefix}|{self.dst_prefix}){self.tbl_prefix})"
        m = re.search(pattern, from_name, flags=re.IGNORECASE)
        return m.group(1) + from_base

    def get_src_table_name(self, table_name: str) -> str:
        base_name = self.get_base_table_name(table_name)
        return f"{self.src_prefix}{self.tbl_prefix}{base_name}"

    def get_src_table_name_from_base_name(self, base_name: str) -> str:
        return f"{self.src_prefix}{self.tbl_prefix}{base_name}"

    def _is_match(self, pattern: str, string: str) -> bool:
        return re.search(pattern, string) is not None

    def is_dst_table(self, table_name: str) -> bool:
        if len(self.dst_prefix) == 0:
            return self._is_match(f"^(?<!{self.src_prefix}){self.tbl_prefix}", table_name)
        return self._is_match(f"^{self.dst_prefix}{self.tbl_prefix}", table_name)

    def is_src_table(self, table_name: str) -> bool:
        return not self.is_dst_table(table_name)

    def get_dst_table_name(self, table_name: str) -> str:
        base_name = self.get_base_table_name(table_name)
        return f"{self.dst_prefix}{self.tbl_prefix}{base_name}"

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

    def get_foreign_keys(self, table_name) -> List[ForeignKey]:
        base_name = self.get_base_table_name(table_name)
        return [fk for fk in self.foreign_keys if fk.src_table == base_name]

    def has_foreign_keys(self, table_name) -> bool:
        base_name = self.get_base_table_name(table_name)
        return any(fk for fk in self.foreign_keys if fk.src_table == base_name)

    def get_table_action(self, table_name: str) -> SyncActions:
        """Returns the sync action for a table."""
        base_name = self.get_base_table_name(table_name)
        return self.get_table_action_from_base_name(base_name)

    def get_table_action_from_base_name(self, base_name: str) -> SyncActions:
        """Returns the sync action for a table."""
        options = self.table_options.get(base_name, {})
        action = options.get("action", self.default_sync_action)
        if self.verify_mode and action == SyncActions.COPY:
            return SyncActions.SKIP
        return action

    def get_update_mode(self, table_name: str) -> UpdateModes:
        """Returns the update mode for this table"""
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        mode = options.get("update_mode", self.default_update_mode)
        return mode

    def get_synthetic_primary_key(self, table_name: str) -> List[str] | None:
        """Returns the synthetic primary key (if any) for a table."""
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        return options.get("synthetic_primary_key")

    def get_synthetic_unique_key(self, table_name: str) -> List[str] | None:
        """Returns the synthetic unique key (if any) for a table."""
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        return options.get("synthetic_unique_key")

    def get_special_rules(self, table_name: str) -> Dict[str, Callable[[str], str]]:
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        return options.get("special_rules")

    def get_use_time_based_comparison(self, table_name: str) -> bool:
        """Returns true if comparison should use timestamp column"""
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        return options.get("use_time_based_comparison", False)

    def get_row_level_action(self, table_name: str, key: List[Any]) -> UpdateActions:
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        actions = options.get("row_level_actions")
        if actions is not None:
            # TODO: inefficient, but we only have 1 action at the moment
            for k, a in actions.items():
                if k == key:
                    return a

        return UpdateActions.DEFAULT

    def get_col_level_actions(self, table_name: str) -> \
            List[Tuple[str, str, UpdateActions]] | None:
        base_name = self.get_base_table_name(table_name)
        options = self.table_options.get(base_name, {})
        actions = options.get("col_level_actions")
        if actions is not None:
            return [(act[0], act[1], act[2]) for act in actions]
        return None

    def dump(self, filename: str) -> None:
        with open(filename, "w", encoding="utf8") as file:
            file.write(self.json())

    @classmethod
    def obj(cls, initial_settings: Self = None, from_filename: str = None):
        global _global_settings

        if _global_settings is None:
            if from_filename is not None:
                _global_settings = Settings.parse_file(from_filename)
            elif initial_settings is not None:
                _global_settings = initial_settings
            else:
                _global_settings = cls()
        elif initial_settings is not None or from_filename is not None:
            msg = "You missed your chance to initialize the settings"
            raise DbSyncParseException(msg)

        return _global_settings

    class Config:
        allow_mutation = True
        json_encoders = {
            types.FunctionType: lambda f: f.__name__
        }


_global_settings: Settings | None = None

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

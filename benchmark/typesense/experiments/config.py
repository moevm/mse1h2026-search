MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "etu",
    "password": "dFwp9779",
    "database": "etu",
    "charset": "utf8mb4",
}

MYSQL_TABLE = "modx_site_content"

MYSQL_COLUMNS = [
    "id",
    "pagetitle",
    "longtitle",
    "description",
    "alias",
    "introtext",
    "content",
    "published",
    "deleted",
    "searchable",
    "parent",
    "template",
]

MYSQL_WHERE = "published = 1 AND deleted = 0 AND searchable = 1"

TYPESENSE_CONFIG = {
    "nodes": [{"host": "localhost", "port": "8108", "protocol": "http"}],
    "api_key": "xyz",
    "connection_timeout_seconds": 120,
}

TYPESENSE_COLLECTION = "site_content"

IMPORT_BATCH_SIZE = 100

COLLECTION_SCHEMA = {
    "name": TYPESENSE_COLLECTION,
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "pagetitle", "type": "string", "index": True},
        {"name": "longtitle", "type": "string", "index": True, "optional": True},
        {"name": "description", "type": "string", "index": True, "optional": True},
        {"name": "introtext", "type": "string", "index": True, "optional": True},
        {
            "name": "content",
            "type": "string",
            "index": True,
            "optional": True,
            "store": False,
        },
        {"name": "pagetitle_lemm", "type": "string", "index": True, "optional": True},
        {"name": "longtitle_lemm", "type": "string", "index": True, "optional": True},
        {"name": "description_lemm", "type": "string", "index": True, "optional": True},
        {"name": "introtext_lemm", "type": "string", "index": True, "optional": True},
        {
            "name": "content_lemm",
            "type": "string",
            "index": True,
            "optional": True,
            "store": False,
        },
        {"name": "lang", "type": "string", "index": True, "optional": True},
        {"name": "alias", "type": "string", "index": False, "optional": True},
        {"name": "parent", "type": "int32", "index": True, "optional": True},
        {"name": "template", "type": "int32", "index": True, "optional": True},
        {"name": "published", "type": "int32", "index": True},
        {"name": "deleted", "type": "int32", "index": True},
        {
            "name": "embedding",
            "type": "float[]",
            "embed": {
                "from": [
                    "pagetitle",
                    "longtitle",
                    "description",
                    "introtext",
                    "content",
                ],
                "model_config": {
                    "model_name": "ts/multilingual-e5-small",
                },
            },
        },
    ],
    "default_sorting_field": "",
    "token_separators": ["-", "/"],
}

SEARCH_PARAMS = {
    "query_by": "pagetitle_lemm,longtitle_lemm,description_lemm,introtext_lemm,content_lemm,embedding",
    "query_by_weights": "10,7,5,4,3,0",
    "vector_query": "embedding:([], alpha: 0.55)",
    "num_typos": 1,
    "min_len_1typo": 4,
    "min_len_2typo": 7,
    "prefix": "false",
    "per_page": 10,
    "filter_by": "published:=1 && deleted:=0",
    "sort_by": "_text_match:desc",
    "prioritize_exact_match": "true",
    "prioritize_token_position": "true",
    "split_join_tokens": "fallback",
    "drop_tokens_threshold": 0,
    "exclude_fields": "embedding",
}

METRICS_K_VALUES = [1, 3, 5, 10]

DEFAULT_QUERIES_JSON = "queries.json"

BASE_URL = "https://etu.ru"

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))

MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3307,
    "user": "root",
    "password": "root",
    "database": "etu_db",
    "use_pure": True,
    "auth_plugin": "mysql_native_password",
}

SOLR_URL = "http://localhost:8983/solr/etu_collection"

SEARCH_PARAMS = {
    "defType": "edismax",
    "qf": "pagetitle^15 longtitle^10 description^5 introtext^3 content^1",
    "rows": 20,
    "mm": "2<-25%",
}

IMPORT_BATCH_SIZE = 200
METRICS_K_VALUES = [1, 5, 10, 20]

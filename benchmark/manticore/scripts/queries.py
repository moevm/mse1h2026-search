# Запрос создания индекса в manticore
MANTICORE_CREATE_TABLE = (
    "CREATE TABLE {table_name} "
    "(pagetitle text, longtitle text, menutitle text, description text, "
    "introtext text, content text, url string, lang string, alias string, parent integer, "
    "content_vector float_vector knn_type='hnsw' knn_dims='384' hnsw_similarity='cosine') "
    "morphology='lemmatize_en, lemmatize_ru, lemmatize_de, libstemmer_fr, "
    "libstemmer_pt, libstemmer_es, libstemmer_ar' ngram_len='1' ngram_chars='cjk' "
    "blend_chars='-, /, &, +, #, @, U+2116, U+0027, U+0060, U+2019' "
    "index_exact_words='1' "
    "wordforms='/etc/wordforms.txt'"
)

# Запрос для выгрузки данных из mysql
MYSQL_SELECT_DOCUMENTS = """
    SELECT id, parent, alias, pagetitle, longtitle, menutitle, description, 
           introtext, content, searchable, type, privateweb 
    FROM modx_site_content 
    WHERE deleted = 0 AND published = 1 AND searchable = 1
"""

MANTICORE_DROP_TABLE = "DROP TABLE IF EXISTS {table_name}"

# основной запрос поиска (лекс.)
MANTICORE_SEARCH_QUERY = """
    SELECT id FROM {table_name}
    WHERE MATCH('{query}')
    LIMIT {limit}
    OPTION field_weights=({weights}), ranker={ranker}
"""

MANTICORE_CHECK_CONNECTION = "SHOW TABLES"

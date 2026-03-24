# Запрос создания индекса в manticore
MANTICORE_CREATE_TABLE = (
    "CREATE TABLE IF NOT EXISTS {table_name} "
    "(pagetitle text, longtitle text, menutitle text, description text, "
    "introtext text, content text, url string, lang string, alias text, parent int) "
    "morphology='lemmatize_en, lemmatize_ru, lemmatize_de, libstemmer_fr, "
    "libstemmer_pt, libstemmer_es, libstemmer_ar' ngram_len='1' ngram_chars='cjk' "
    "blend_chars='-, /, &, +, #, @, U+2116, U+0027, U+0060, U+2019' "
    "min_prefix_len='3' "
    "index_exact_words='1' "
    "wordforms='/etc/wordforms.txt' "
)

# Запрос для выгрузки данных из mysql
MYSQL_SELECT_DOCUMENTS = """
    SELECT id, parent, alias, pagetitle, longtitle, menutitle, description, 
           introtext, content, searchable, type, privateweb 
    FROM modx_site_content 
    WHERE deleted = 0 AND published = 1 AND searchable = 1
"""

MANTICORE_DROP_TABLE = "DROP TABLE IF EXISTS {table_name}"

# основной запрос поиска
MANTICORE_SEARCH_QUERY = """
    SELECT id FROM {table_name}
    WHERE MATCH('{query}')
    LIMIT {limit}
    OPTION field_weights=({weights}), ranker={ranker}
"""

MANTICORE_CHECK_CONNECTION = "SHOW TABLES"

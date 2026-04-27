class IndexerError(Exception):
    """Базовый класс для всех ошибок модуля индексации."""
    pass


class DatabaseExtractionError(IndexerError):
    """Ошибка при выгрузке данных из источника (CMS)."""
    pass

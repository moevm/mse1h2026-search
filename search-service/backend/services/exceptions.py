class SearchProviderError(Exception):
    """Base exception for all search provider errors."""
    pass


class InvalidParameterError(SearchProviderError):
    """Raised when an invalid parameter is passed to a search provider."""
    pass

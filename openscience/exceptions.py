class OpenScienceException(Exception):
    """
    Base class for all exceptions in the `openscience` package.
    """

    pass


class SemanticScholarEntryInaccessible(OpenScienceException):
    """
    Raised when an entry is inaccessible from the Semantic Scholar
    API.
    """

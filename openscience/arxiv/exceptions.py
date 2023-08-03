from openscience.exceptions import OpenScienceException


class ArxivException(OpenScienceException):
    """
    Base class for all arXiv-related exceptions.
    """

    pass


class ArxivUnsupportedEntryID(ArxivException):
    """
    Raised when an entry ID is not supported by the arXiv data source.
    """

    pass


class ArxivEntryNotFound(ArxivException):
    """
    Raised when an entry is not found in the arXiv data source.
    """

    pass
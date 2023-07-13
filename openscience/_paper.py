from __future__ import annotations

import requests

import pydantic

from openscience.util import url_join
from openscience.arxiv import ArxivDataSource, ArxivWorkingContext, GzipArxivEntry
from openscience.exceptions import SemanticScholarEntryInaccessible, OpenScienceException


ArxivDataSourceOrContext = ArxivDataSource | ArxivWorkingContext
"""
One of `ArxivDataSource` or `ArxivWorkingContext`. Represents an object
which provides a `load_entry()` method for specific access to arXiv data.
"""


class PaperMetadata(pydantic.BaseModel):
    abstract: str
    arxivId: str
    authors: list[Author]
    title: str
    year: int


class Author(pydantic.BaseModel):
    authorId: str
    name: str
    url: str


class Paper:
    arxiv_id: str
    meta: PaperMetadata
    """
    Metadata collected from the Semantic Scholar API.
    """

    def __init__(
        self, arxiv_id: str, *, semscholar_api_base_url: str = "https://api.semanticscholar.org/v1/"
    ) -> None:
        self.arxiv_id = arxiv_id

        # Populate the paper's metadata from the Semantic Scholar API.

        try:
            response = requests.get(url_join(semscholar_api_base_url, f"paper/arXiv:{arxiv_id}"))

            if not response.ok:
                raise SemanticScholarEntryInaccessible(
                    f"endpoint returned HTTP status code {response.status_code}"
                )

            self.meta = PaperMetadata(**response.json())
        except requests.exceptions.ConnectionError as e:
            raise SemanticScholarEntryInaccessible from e

    def load_full_text(self, source: ArxivDataSourceOrContext) -> str:
        """
        Loads the full text of the paper from the given source.
        """

        entry = source.load_entry(self.arxiv_id)

        if isinstance(entry, GzipArxivEntry):
            return entry.contents
        else:
            raise OpenScienceException(
                f"entry {self.arxiv_id} does not have full text available"
            )

    def load_latex(self, source: ArxivDataSourceOrContext) -> str:
        """
        Loads the LaTeX source of the paper from the given source.
        """

        raise NotImplementedError

    @property
    def title(self) -> str:
        """
        Shortcut for `self.meta.title`.
        """

        return self.meta.title

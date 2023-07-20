"""
TODO:
 - harmonize in fields from metadataPrefix=arXiv
 - easy way to iterate through everything?
"""

from functools import cached_property
import typing as t
from datetime import date
from dataclasses import field
import asyncio
import time

import bs4
import aiohttp
from pydantic.dataclasses import dataclass
from tqdm.auto import tqdm

VALID_METADATA_PREFIXES = ("oai_dc", "arXiv")
PREFIX_DEFAULT = "oai_dc"
PAGING_BACKOFF = 4

def get_text(soup: bs4.BeautifulSoup, find: str, required: bool=False) -> t.Optional[str]:
    if match := soup.find(find):
        return match.text
    if required:
        raise RuntimeError(f"Tag {find} not found.")

def get_texts(soup: bs4.BeautifulSoup, find: str) -> list[str]:
    return [
        match.text for match in soup.find_all(find)
    ]

@dataclass
class OAIMetadata:
    oai_identifier: t.Optional[str]
    oai_specs: list[str]
    oai_datestamp: t.Optional[date]
    title: str
    creators: list[str]
    subjects: list[str]
    descriptions: list[str] = field(repr=False)
    dates: list[date]
    identifiers: list[str]

    @classmethod
    def from_soup(
        cls,
        soup: bs4.BeautifulSoup,
        prefix: t.Literal[VALID_METADATA_PREFIXES],
    ) -> 'OAIMetadata':
        # TODO: harmonize prefixes
        header = soup.find("header")
        if prefix == "arXiv":
            metadata = soup.find("metadata").find("arXiv")
        elif prefix == "oai_dc":
            metadata = soup.find("metadata").find("oai_dc:dc")
        return cls(
            oai_identifier=get_text(header, "identifier"),
            oai_specs=get_texts(header, "setSpec"),
            oai_datestamp=get_text(header, "datestamp"),
            title=get_text(metadata, "title"),
            creators=get_texts(metadata, "creator"),
            subjects=get_texts(metadata, "subject"),
            descriptions=get_texts(metadata, "description"),
            dates=get_texts(metadata, "date"),
            identifiers=get_texts(metadata, "identifier"),
        )

class ArxivOAIClient:
    def __init__(self, url: str="https://export.arxiv.org/oai2", concurrency_limit: int=3):
        self.url = url
        self.concurrency_limit = 3

    @cached_property
    def session(self):
        connector = aiohttp.TCPConnector(limit_per_host=self.concurrency_limit)
        return aiohttp.ClientSession(connector=connector)

    async def get_record(
        self,
        identifier: str,
        prefix: t.Literal[VALID_METADATA_PREFIXES]=PREFIX_DEFAULT,
    ) -> OAIMetadata:
        assert prefix in VALID_METADATA_PREFIXES
        params = {
            "verb": "GetRecord",
            "identifier": identifier,
            "metadataPrefix": prefix,
        }
        async with self.session.get(self.url, params=params, raise_for_status=True) as resp:
            text = await resp.text()
            soup = bs4.BeautifulSoup(text, "xml")
            record = soup.find("GetRecord").find("record")
            return OAIMetadata.from_soup(record, prefix=prefix)

    async def list_records(
        self,
        from_: date,
        until: date,
        set_: t.Optional[str]=None,
        prefix: t.Literal[VALID_METADATA_PREFIXES]=PREFIX_DEFAULT,
        progress: bool=False,
    ) -> t.AsyncIterator[OAIMetadata]:
        assert prefix in VALID_METADATA_PREFIXES
        params = {
            "verb": "ListRecords",
            "from": from_.strftime("%Y-%m-%d"),
            "until": until.strftime("%Y-%m-%d"),
            "metadataPrefix": prefix,
        }
        if set_ is not None:
            params["set"] = set_
        with tqdm(disable=not progress) as pbar:
            while True:
                async with self.session.get(self.url, params=params, raise_for_status=True) as resp:
                    response_t = time.perf_counter()
                    text = await resp.text()
                    soup = bs4.BeautifulSoup(text, "xml")
                    resumption_token = soup.find("resumptionToken")
                    if pbar.total is None and resumption_token:
                        pbar.reset(total=int(resumption_token.attrs["completeListSize"]))
                    for record in soup.find("ListRecords").find_all("record"):
                        yield OAIMetadata.from_soup(record, prefix=prefix)
                        pbar.update()
                    if resumption_token and resumption_token.text:
                        params = {
                            "verb": "ListRecords",
                            "resumptionToken": resumption_token.text,
                        }
                        # wait one more second from the end of prev request
                        #  but include any time taken iterating through results
                        elapsed = time.perf_counter() - response_t
                        await asyncio.sleep(PAGING_BACKOFF - elapsed)
                    else:
                        break

# pylint: disable=missing-function-docstring,missing-class-docstring,invalid-name
"""
TODO:
 - easy way to iterate through everything?
"""

from functools import cached_property
import typing as t
from datetime import date
import asyncio
import time

import aiohttp
from tqdm.auto import tqdm
import pydantic
import xmltodict

VALID_METADATA_PREFIXES = ("oai_dc", "arXiv")
PREFIX_DEFAULT = "arXiv"
PAGING_BACKOFF = 4

# deprecated pydantic v1 utils
def to_camel(string: str) -> str:
    return ''.join(word.capitalize() for word in string.split('_'))

def to_lower_camel(string: str) -> str:
    if len(string) >= 1:
        pascal_string = to_camel(string)
        return pascal_string[0].lower() + pascal_string[1:]
    return string.lower()

class Set(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=to_lower_camel)
    set_spec: str
    set_name: str

class DublinCoreMetadata(pydantic.BaseModel):
    # spec at http://www.openarchives.org/OAI/2.0/oai_dc.xsd
    model_config = pydantic.ConfigDict(
        alias_generator=lambda s: 'dc:' + s.rstrip("_").replace("_", "-"))
    title: str | list[str] | None = None
    creator: str | list[str] | None = None
    subject: str | list[str] | None = None
    description: str | list[str] | None = None
    publisher: str | list[str] | None = None
    contributor: str | list[str] | None = None
    date: str | list[str] | None = None
    type_: str | list[str] | None = None
    format_: str | list[str] | None = None
    identifier: str | list[str] | None = None
    source: str | list[str] | None = None
    language: str | list[str] | None = None
    relation: str | list[str] | None = None
    coverage: str | list[str] | None = None
    rights: str | list[str] | None = None

class arXivAuthor(pydantic.BaseModel):
    keyname: str | None = None
    forenames: str | None = None

class arXivMetadata(pydantic.BaseModel):
    # spec at https://arxiv.org/OAI/arXiv.xsd
    model_config = pydantic.ConfigDict(alias_generator=lambda s: s.rstrip("_").replace("_", "-"))
    id_: str
    created: str | None = None
    updated: str | None = None
    authors: arXivAuthor | list[arXivAuthor] | None = None
    title: str | None = None
    msc_class: str | None = None
    acm_class: str | None = None
    report_no: str | None = None
    journal_ref: str | None = None
    comments: str | None = None
    abstract: str | None = None
    categories: str | None = None
    doi: str | None = None
    proxy: str | None = None
    license_: str | None = None

class Header(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(alias_generator=to_lower_camel)
    identifier: str | None = None
    set_spec: str | list[str] | None = None
    datestamp: date | None = None

class MetadataRecord(pydantic.BaseModel):
    header: Header
    metadata: arXivMetadata | DublinCoreMetadata
    @classmethod
    def from_record(cls, record: dict, prefix: t.Literal['arXiv', 'oai_dc']):
        if prefix == 'arXiv':
            metadata = record['metadata']['arXiv']
            metadata |= {'authors': metadata['authors']['author']}
            metadata = arXivMetadata(**metadata)
        elif prefix == 'oai_dc':
            metadata = record['metadata']['oai_dc:dc']
            metadata = {k: v for k, v in metadata.items() if not k.startswith('@')}
            metadata = DublinCoreMetadata(**metadata)
        return cls(header=record['header'], metadata=metadata)

class ArxivOAIClient:
    def __init__(self, url: str="https://export.arxiv.org/oai2", concurrency_limit: int=3):
        self.url = url
        self.concurrency_limit = concurrency_limit

    @cached_property
    def session(self):
        connector = aiohttp.TCPConnector(limit_per_host=self.concurrency_limit)
        return aiohttp.ClientSession(connector=connector)

    async def list_sets(self) -> list[Set]:
        params = {"verb": "ListSets"}
        async with self.session.get(self.url, params=params, raise_for_status=True) as resp:
            text = await resp.text()
            results = xmltodict.parse(text)['OAI-PMH']['ListSets']['set']
            return [Set(**result) for result in results]

    async def get_record(
        self,
        identifier: str,
        prefix: t.Literal[VALID_METADATA_PREFIXES]=PREFIX_DEFAULT,
    ) -> MetadataRecord:
        assert prefix in VALID_METADATA_PREFIXES
        params = {
            "verb": "GetRecord",
            "identifier": identifier,
            "metadataPrefix": prefix,
        }
        async with self.session.get(self.url, params=params, raise_for_status=True) as resp:
            text = await resp.text()
            data = xmltodict.parse(text)
            record = data['OAI-PMH']['GetRecord']['record']
            return MetadataRecord.from_record(record, prefix=prefix)

    async def list_records(
        self,
        from_: date,
        until: date,
        set_: t.Optional[str]=None,
        prefix: t.Literal[VALID_METADATA_PREFIXES]=PREFIX_DEFAULT,
        progress: bool=False,
    ) -> t.AsyncIterator[MetadataRecord]:
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
                async with self.session.get(self.url, params=params) as resp:
                    if resp.status == 503:
                        await asyncio.sleep(5)
                        continue
                    resp.raise_for_status()
                    response_t = time.perf_counter()
                    data = xmltodict.parse(await resp.text())
                    list_records = data['OAI-PMH']['ListRecords']
                    resumption_token = list_records.get('resumptionToken')
                    if pbar.total is None and resumption_token:
                        pbar.reset(total=int(resumption_token['@completeListSize']))
                    for record in list_records["record"]:
                        yield MetadataRecord.from_record(record, prefix=prefix)
                        pbar.update()
                    if resumption_token and resumption_token.get('#text'):
                        params = {
                            "verb": "ListRecords",
                            "resumptionToken": resumption_token.get('#text'),
                        }
                        # wait one more second from the end of prev request
                        #  but include any time taken iterating through results
                        elapsed = time.perf_counter() - response_t
                        await asyncio.sleep(PAGING_BACKOFF - elapsed)
                    else:
                        break

from __future__ import annotations

import os
import shutil
import re
from glob import glob

import xmltodict
import pydantic

from openscience.arxiv._fsutil import unpack_gz, unpack_tar
from openscience.arxiv.exceptions import ArxivUnsupportedEntryID, ArxivEntryNotFound


TMP_DIR = "/tmp/arxiv"


def get_temp_dir() -> str:
    """
    Returns the path to the temporary directory where arXiv data is stored.
    """

    return TMP_DIR


def clear_temp_dir() -> None:
    """
    Clears the temporary directory where arXiv data is stored.
    """

    shutil.rmtree(TMP_DIR)
    os.mkdir(TMP_DIR)


ArxivID = str


class BaseArxivEntry:
    """
    Base class for all arXiv entries, i.e. entires found in the
    arXiv tarballs.
    """

    id: ArxivID
    """
    The arXiv ID of the entry, e.g. `2101.00001`.
    """

    def __init__(self, id: ArxivID) -> None:
        self.id = id


class GzipArxivEntry(BaseArxivEntry):
    """
    Represents an arXiv entry that is stored in a .gz file.
    """

    path: str
    contents: str

    def __init__(self, id: ArxivID, path: str) -> None:
        super().__init__(id)
        self.path = path

        unpack_dest = os.path.join(TMP_DIR, id)
        unpack_gz(path, unpack_dest)

        with open(unpack_dest) as f:
            self.contents = f.read()


class _ArxivTarball:
    """
    Class representing a single `.tar` file in the arXiv dataset.
    Takes the form `arXiv_src_XXXX_XXX.tar`. For internal use only.
    """

    path: str
    """
    The underlying path to the corresponding `.tar` file.
    """

    def __init__(self, path: str) -> None:
        self.path = path

    def load_entry(self, entry_id: ArxivID) -> BaseArxivEntry | None:
        """
        Fetches a single entry from the tarball. If the corresponding entry
        does not exist in this tarball, returns `None` instead.
        """

        self._assert_unpacked()

        # Look for the entry in the unpacked directory

        candidate_paths = glob(os.path.join(self._get_unpacked_dir_path(), f"{entry_id}.*"))

        if len(candidate_paths) == 0:
            return None

        if len(candidate_paths) > 1:
            raise RuntimeError(
                f"Found multiple entries with ID {entry_id} in tarball {self.name}: {candidate_paths!r}"
            )

        path = candidate_paths[0]

        # Use the file extension to determine the entry type

        path_ext = os.path.splitext(path)[1]

        if path_ext == ".gz":
            return GzipArxivEntry(entry_id, path)
        else:
            raise RuntimeError(f"Unknown file extension {path_ext} for entry {entry_id}")

    def get_entry_ids(self) -> list[ArxivID]:
        """
        Returns a list of all entry IDs in this tarball.
        """

        self._assert_unpacked()

        paths = os.listdir(self._get_unpacked_dir_path())
        return [os.path.splitext(path)[0] for path in paths]

    @property
    def name(self) -> str:
        """
        The name of the tarball, e.g. `arXiv_src_2101_001.tar`.
        """

        return os.path.basename(self.path)

    def _get_unpacked_dir_path(self) -> str:
        """
        Returns the path to the directory where the unpacked data for this tarball
        should be stored. The path returned is not guaranteed to exist.
        """

        return os.path.join(TMP_DIR, os.path.splitext(self.name)[0])

    def _is_unpacked(self) -> bool:
        """
        Returns whether the tarball has been unpacked.
        """

        return os.path.exists(self._get_unpacked_dir_path())

    def _assert_unpacked(self) -> None:
        """
        Raises a `RuntimeError` if the tarball has not been unpacked.
        """

        if not self._is_unpacked():
            raise RuntimeError(
                f"Tarball {self.name} has not been unpacked. "
                "Call `unpack()` before fetching entries."
            )

    def unpack(self) -> None:
        """
        Unpack the contents of this tarball into the filesystem. This method
        must be called prior to fetching entries from the tarball.

        - The unpacked data is stored in the temporary directory, whose path is
        given by `arxiv.get_temp_dir()`.

        - If this tarball has already been unpacked, this method does nothing.
        """

        if self._is_unpacked():
            return

        os.makedirs(self._get_unpacked_dir_path())

        unpack_tar(self.path, self._get_unpacked_dir_path())

    def delete(self) -> None:
        """
        Deletes the unpacked tarball from the filesystem. Does not
        delete the tarball itself, only the unpacked data.
        """

        shutil.rmtree(self._get_unpacked_dir_path())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ArxivTarball):
            return NotImplemented

        return self.path == other.path


class _ManifestEntry(pydantic.BaseModel):
    num_items: int
    yymm: str
    seq_num: int
    first_item: str
    last_item: str

    @property
    def filename(self) -> str:
        return f"arXiv_src_{self.yymm}_{self.seq_num:03d}.tar"


class _ArxivDataSourceManifest:
    manifest_xml_path: str

    _entries: dict[str, list[_ManifestEntry]]
    """
    Maps a YYMM string to a list of manifest entries for that month.
    """

    def __init__(self, manifest_xml_path: str) -> None:
        self.manifest_xml_path = manifest_xml_path

        with open(manifest_xml_path) as f:
            manifest_data = xmltodict.parse(f.read())

        # Populate self._entries

        self._entries = {}

        for entry_data in manifest_data["arXivSRC"]["file"]:
            entry = _ManifestEntry(**entry_data)
            key = entry.yymm

            if key not in self._entries:
                self._entries[key] = []

            self._entries[key].append(entry)

        # Sort each list of entries by sequence number

        for key in self._entries:
            self._entries[key].sort(key=lambda entry: entry.seq_num)

    def get_tarball_path_for_entry(self, entry_id: ArxivID) -> str:
        """
        Returns the path to the tarball containing the given entry.
        """

        # Validate that the entry_id is of the form "YYMM.XXXXX"

        if not re.match(r"\d{4}\.\d{5}", entry_id):
            raise ArxivUnsupportedEntryID(
                f"Entry ID {entry_id} must be of the form YYMM.XXXXX (e.g. 2101.00001) in order for it to be retrieved from the data source."
            )

        # Get the YYMM string from the entry ID

        yymm = entry_id.split(".")[0]
        num = int(entry_id.split(".")[1])

        # Find the manifest entry for the given entry ID using the YYMM string

        manifest_entries = self._entries.get(yymm, [])

        if len(manifest_entries) == 0:
            raise ArxivEntryNotFound(
                f"Entry {entry_id} does not exist in data source: no manifest entry was found for YYMM {yymm}"
            )

        # Look through each manifest entry obtained from the above step. Find the one
        # for which `num` is in the range provided by entry.first_item and entry.last_item.

        for entry in manifest_entries:
            try:
                first_item = int(entry.first_item.split(".")[1])
                last_item = int(entry.last_item.split(".")[1])
            except:
                raise ArxivUnsupportedEntryID(
                    f"Manifest entry for tarball {entry.filename} has invalid first_item or last_item: {entry.first_item}, {entry.last_item}. first_item and last_item must be of the form YYMM.XXXXX (e.g. 2101.00001) in order for entries to be retrieved from the data source."
                )

            if num >= first_item and num <= last_item:
                return os.path.join(os.path.dirname(self.manifest_xml_path), entry.filename)

        raise ArxivEntryNotFound(
            f"Entry {entry_id} does not exist in data source: no manifest entry was found for YYMM {yymm} containing item {num}"
        )


class ArxivDataSource:
    source_path: str
    """
    The underlying path to the data source.
    """

    _manifest: _ArxivDataSourceManifest

    def __init__(self, source_path: str) -> None:
        self.source_path = os.path.abspath(source_path)

        # Validate existence of provided path

        if not os.path.exists(source_path):
            raise ValueError(f"Data source {source_path} does not exist.")

        # Load manifest

        manifest_xml_path = os.path.join(source_path, "arXiv_src_manifest.xml")

        if not os.path.exists(manifest_xml_path):
            raise ValueError(
                f"Data source {source_path} does not contain a manifest file. Is this a valid arXiv data source?"
            )

        self._manifest = _ArxivDataSourceManifest(manifest_xml_path)

    def get_tarball_for_entry(self, entry_id: ArxivID) -> _ArxivTarball:
        """
        Returns the tarball containing the given entry.
        """

        tarball_path = self._manifest.get_tarball_path_for_entry(entry_id)
        return _ArxivTarball(tarball_path)

    def load_entry(self, entry_id: ArxivID) -> BaseArxivEntry:
        """
        Loads a single entry from the data source. This method is inefficient
        for batch calls and should only be used for loading single entries.

        If the entry does not exist, raises a `ValueError`.
        """

        tarball = self.get_tarball_for_entry(entry_id)
        tarball.unpack()

        entry = tarball.load_entry(entry_id)

        if entry is None:
            raise ValueError(f"Entry {entry_id} does not exist in data source.")

        tarball.delete()

        return entry

    def new_context(self) -> ArxivWorkingContext:
        """
        Returns a new working context for this data source. The working context
        can be used to load entries from the data source in an efficient manner.
        """

        return ArxivWorkingContext(self)


class ArxivWorkingContext:
    """
    Context manager for working with arXiv data. This class is not meant to be
    used directly; instead, use `ArxivDataSource.new_context()` to create a working
    context.
    """

    _open_tarballs: list[_ArxivTarball]
    _data_source: ArxivDataSource

    def __init__(self, data_source: ArxivDataSource) -> None:
        self._open_tarballs = []
        self._data_source = data_source

    def load_entry(self, entry_id: ArxivID) -> BaseArxivEntry:
        """
        Loads a single entry from the data source. This method is inefficient
        for batch calls and should only be used for loading single entries.

        If the entry does not exist, raises a `ValueError`.
        """

        tarball = self._data_source.get_tarball_for_entry(entry_id)

        if tarball not in self._open_tarballs:
            tarball.unpack()
            self._open_tarballs.append(tarball)

        entry = tarball.load_entry(entry_id)

        if entry is None:
            raise ValueError(f"Entry {entry_id} does not exist in data source.")

        return entry

    def __enter__(self) -> ArxivWorkingContext:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        for tarball in self._open_tarballs:
            tarball.delete()

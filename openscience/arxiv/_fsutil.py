import os
import gzip

from openscience.util import run_process, run_process_shell


def unpack_tar(tar_path: str, destination_dir: str) -> None:
    """
    Unpacks a `.tar` file into the given directory.
    """

    result = run_process(["tar", "-xf", tar_path, "-C", destination_dir, "--strip-components=1"])

    if result.returncode != 0:
        raise RuntimeError(f"Failed to unpack tarball {tar_path}:\n{result.stderr}")


def unpack_gz(gz_path: str, destination: str) -> None:
    """
    Unpacks a `.gz` file into the given file.
    """

    with gzip.open(gz_path, "rb") as gz_file:
        with open(destination, "wb") as dest_file:
            dest_file.write(gz_file.read())
import subprocess
from dataclasses import dataclass


@dataclass
class ProcessResult:
    stdout: str
    stderr: str
    returncode: int


def run_process(argv: list[str | int]) -> ProcessResult:
    """
    Runs a process and returns the result.

    - `argv`: The command to run, as a list of strings.
    """

    result = subprocess.run(
        [str(arg) for arg in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )

    return ProcessResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


def run_process_shell(command: str) -> ProcessResult:
    """
    Runs a process and returns the result.

    - `command`: The command to run, as a string.
    """

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        shell=True,
    )

    return ProcessResult(
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
    )


def url_join(*args) -> str:
    """
    Joins a list of strings into a URL, ensuring that there is only one '/' between each part of the URL.

    ```
    >>> url_join("https://omnilabs.ai", "api", "v1", "users")
    "https://omnilabs.ai/api/v1/users"
    >>> url_join("https://omnilabs.ai/", "/api/", "/v1/", "/users/")
    "https://omnilabs.ai/api/v1/users"
    ```
    """

    return "/".join(map(lambda x: str(x).rstrip("/"), args))

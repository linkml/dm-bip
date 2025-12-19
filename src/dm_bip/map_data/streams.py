"""Data structures for creating streamed output from chunked input data."""

import abc
import json
from typing import Any, Generator, Iterator, Literal

import yaml
from flatten_dict import flatten
from flatten_dict.reducers import make_reducer

StreamFormat = Literal["json", "jsonl", "tsv", "yaml"]
Chunk = list[dict[str, Any]]
Chunks = Iterator[Chunk]
StreamOutput = Generator[str, None, None]


def make_stream(fmt: StreamFormat, **kwargs) -> "Stream":
    """
    Create a data stream.

    Note: kwargs are validated at runtime, not enforced at the callsite. This was on purpose, to make construction at
    the callsite more ergonomic. In the future, we may want to ditch this function, and just enforce type safety at
    the callsite.
    """
    match fmt:
        case "json":
            key_name = kwargs.get("key_name")
            if not isinstance(key_name, str):
                raise TypeError("String key name required for JSON stream.")
            return JSONStream(key_name=key_name)

        case "yaml":
            key_name = kwargs.get("key_name")
            if not isinstance(key_name, str):
                raise TypeError("String key name required for YAML stream.")
            return YAMLStream(key_name=key_name)

        case "tsv":
            sep = kwargs.get("sep", "\t")
            reducer_str = kwargs.get("reducer_str", "__")
            if not isinstance(sep, str) or not isinstance(reducer_str, str):
                raise TypeError("Invalid TSV parameters")
            return TSVStream(sep=sep, reducer_str=reducer_str)

        case "jsonl":
            return JSONLStream()

        case _:
            raise ValueError("Invalid stream format.")


class Stream(abc.ABC):
    """Serialize chunks into an output format."""

    @abc.abstractmethod
    def process(self, chunks: Chunks) -> StreamOutput:
        """Process a series of chunks."""
        ...


class JSONStream(Stream):
    """Convert chunks of objects to JSON format."""

    def __init__(self, key_name: str):
        """Initialize with key name."""
        self.key_name = key_name

    def process(self, chunks: Chunks) -> StreamOutput:
        """Serialize the output."""
        for i, chunk in enumerate(chunks):
            js = json.dumps({self.key_name: chunk}, ensure_ascii=False)
            yield js if i == 0 else ",".join(js.splitlines()[1:-1])


class YAMLStream(Stream):
    """Convert chunks of objects to YAML format."""

    def __init__(self, key_name: str):
        """Initialize with key name."""
        self.key_name = key_name

    def process(self, chunks: Chunks) -> StreamOutput:
        """Serialize the output."""
        for i, chunk in enumerate(chunks):
            yaml_str = yaml.dump({self.key_name: chunk}, default_flow_style=False)
            yield yaml_str if i == 0 else "\n".join(yaml_str.splitlines()[1:]) + "\n"


class JSONLStream(Stream):
    """Convert chunks of objects to JSONL format."""

    def process(self, chunks: Chunks) -> StreamOutput:
        """Serialize the output."""
        for chunk in chunks:
            yield "".join(json.dumps(obj, ensure_ascii=False) + "\n" for obj in chunk)


class TSVStream(Stream):
    """Convert chunks of objects to TSV format."""

    def __init__(self, sep: str, reducer_str: str):
        """Initialize with TSV-specific parameters."""
        self.sep = sep
        self.reducer = make_reducer(reducer_str)
        self.current_headers: list[str] | None = None
        self.next_headers: list[str] = []
        self.must_update_headers = False

    def process(self, chunks: Chunks) -> StreamOutput:
        """Serialize the output."""
        for chunk in chunks:
            for obj in chunk:
                flat = flatten(obj, reducer=self.reducer)  # type: ignore

                for k in flat.keys():
                    if k not in self.next_headers:
                        self.next_headers.append(k)

                # Set headers on initial run
                if self.current_headers is None:
                    yield self.sep.join(self.next_headers) + "\n"
                    self.current_headers = list(self.next_headers)

                row = self.sep.join(str(flat.get(h, "")) for h in self.current_headers)
                yield row + "\n"

        if self.current_headers != self.next_headers:
            self.must_update_headers = True

    @staticmethod
    def rewrite_header_and_pad(chunks: Iterator[list[str]], new_headers: list[str], sep="\t") -> StreamOutput:
        """Rewrite the header of TSV chunks and pad rows with missing columns."""
        header_count = len(new_headers)

        def pad_lines(chunk: list[str]):
            """Pad each row in a chunk to match the final header width."""
            for line in chunk:
                fields = line.rstrip("\n").split(sep)
                if len(fields) < header_count:
                    fields.extend([""] * (header_count - len(fields)))
                yield sep.join(fields) + "\n"

        # Emit the new header line
        yield sep.join(new_headers) + "\n"

        # Skip the first line in the first chunk (the header line)
        first_chunk = next(chunks, None)
        if first_chunk is None:
            return
        first_chunk = first_chunk[1:]
        yield from pad_lines(first_chunk)

        for chunk in chunks:
            yield from pad_lines(chunk)

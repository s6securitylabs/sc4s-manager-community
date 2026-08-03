#!/usr/bin/env python3
"""Build the Commvault event-code Splunk lookup from official documentation.

Commvault "Events" syslog records carry an ``Eventcode`` field shaped like
``<subsystem_id>:<message_id>`` (for example ``30:359``). The authoritative
mapping from code to event string lives in the Commvault documentation page
"System Messages, Event Strings and Error Codes":

    https://documentation.commvault.com/2024e/commcell-console/system_messages_event_strings_and_error_codes.html

This script converts that page (fetched live, from a saved HTML copy, or from
a tab-separated text export of the page when the docs site is unreachable or
bot-gated) into ``splunk/lookups/commvault_eventcodes.csv`` so Splunk can
enrich ``Eventcode`` with a human-readable ``event_string``.

Usage examples:

    # Fetch the official page directly (needs outbound HTTPS to commvault.com)
    python3 build_commvault_eventcode_lookup.py

    # Parse a manually saved copy of the page instead
    python3 build_commvault_eventcode_lookup.py --html-file system_messages.html

    # Parse several saved sub-pages and merge with the existing CSV rows
    python3 build_commvault_eventcode_lookup.py --html-file part1.html --html-file part2.html

    # Parse a text export: "<subsystem>:<message><TAB><event string>" per line,
    # section headings and "Code<TAB>Description" header lines are ignored
    python3 build_commvault_eventcode_lookup.py --text-file system_messages.txt

The parser is deliberately tolerant: it scans every HTML table for rows whose
first cell looks like an event code and treats the next non-empty cell as the
event string. Rows already present in the output CSV are preserved unless the
same code is re-scraped (newest parse wins), so partial/manual seed rows are
never silently lost. Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_URL = (
    "https://documentation.commvault.com/2024e/commcell-console/"
    "system_messages_event_strings_and_error_codes.html"
)
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "splunk" / "lookups" / "commvault_eventcodes.csv"
DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) sechub-resources-lookup-builder/1.0"

EVENT_CODE_RE = re.compile(r"^\s*(\d{1,4})\s*:\s*(\d{1,5})\s*$")
TEXT_LINE_RE = re.compile(r"^\s*(\d{1,4})\s*:\s*(\d{1,5})\s*\t\s*(.*\S)\s*$")
CSV_FIELDS = ["event_code", "subsystem_id", "message_id", "event_string"]


class TableParser(HTMLParser):
    """Collect text content of every table row on the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._in_cell = False
        self._cell_chunks: list[str] = []
        self._current_row: list[str] = []
        self._row_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "tr":
            self._row_depth += 1
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cell_chunks = []
        elif tag == "br" and self._in_cell:
            self._cell_chunks.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._in_cell:
            self._in_cell = False
            text = re.sub(r"\s+", " ", "".join(self._cell_chunks)).strip()
            self._current_row.append(text)
        elif tag == "tr" and self._row_depth > 0:
            self._row_depth -= 1
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_chunks.append(data)


def extract_codes(html: str) -> dict[str, dict[str, str]]:
    """Return {event_code: row_dict} for every table row that maps a code to a string."""
    parser = TableParser()
    parser.feed(html)
    found: dict[str, dict[str, str]] = {}
    for row in parser.rows:
        if not row:
            continue
        match = EVENT_CODE_RE.match(row[0])
        if not match:
            continue
        event_string = next((cell for cell in row[1:] if cell), "")
        if not event_string:
            continue
        subsystem_id, message_id = match.group(1), match.group(2)
        code = f"{subsystem_id}:{message_id}"
        found[code] = {
            "event_code": code,
            "subsystem_id": subsystem_id,
            "message_id": message_id,
            "event_string": event_string,
        }
    return found


def extract_codes_text(text: str) -> dict[str, dict[str, str]]:
    """Parse a tab-separated text export: one '<code>\\t<event string>' per line."""
    found: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        match = TEXT_LINE_RE.match(line)
        if not match:
            continue
        subsystem_id, message_id = match.group(1), match.group(2)
        event_string = re.sub(r"\s+", " ", match.group(3)).strip()
        code = f"{subsystem_id}:{message_id}"
        found[code] = {
            "event_code": code,
            "subsystem_id": subsystem_id,
            "message_id": message_id,
            "event_string": event_string,
        }
    return found


def fetch(url: str, timeout: int, user_agent: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-supplied docs URL
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return {
            row["event_code"]: {field: row.get(field, "") for field in CSV_FIELDS}
            for row in reader
            if row.get("event_code")
        }


def write_csv(path: Path, rows: dict[str, dict[str, str]]) -> None:
    def sort_key(code: str) -> tuple[int, int]:
        subsystem, _, message = code.partition(":")
        return int(subsystem), int(message)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for code in sorted(rows, key=sort_key):
            writer.writerow(rows[code])


def main(argv: list[str] | None = None) -> int:
    arg_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument("--url", action="append", default=[], help=f"Documentation page URL to fetch (default: {DEFAULT_URL})")
    arg_parser.add_argument("--html-file", action="append", default=[], type=Path, help="Saved HTML copy of the documentation page to parse instead of fetching")
    arg_parser.add_argument("--text-file", action="append", default=[], type=Path, help="Tab-separated text export of the documentation page ('<code>\\t<event string>' per line) to parse instead of fetching")
    arg_parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Output lookup CSV path (default: {DEFAULT_OUT})")
    arg_parser.add_argument("--no-merge", action="store_true", help="Discard rows already in the output CSV instead of merging")
    arg_parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds (default: 60)")
    arg_parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent header for fetches")
    args = arg_parser.parse_args(argv)

    documents: list[tuple[str, str, str]] = []
    for html_path in args.html_file:
        documents.append((str(html_path), html_path.read_text(encoding="utf-8", errors="replace"), "html"))
    for text_path in args.text_file:
        documents.append((str(text_path), text_path.read_text(encoding="utf-8", errors="replace"), "text"))
    urls = args.url or ([] if (args.html_file or args.text_file) else [DEFAULT_URL])
    for url in urls:
        print(f"[fetch] {url}", file=sys.stderr)
        try:
            documents.append((url, fetch(url, args.timeout, args.user_agent), "html"))
        except Exception as exc:  # noqa: BLE001 - report and fail with guidance
            print(
                f"error: could not fetch {url}: {exc}\n"
                "hint: save the page from a browser and re-run with --html-file <saved.html> or --text-file <saved.txt>",
                file=sys.stderr,
            )
            return 2

    if not documents:
        print("error: nothing to parse; pass --url, --html-file, and/or --text-file", file=sys.stderr)
        return 2

    rows: dict[str, dict[str, str]] = {} if args.no_merge else load_existing(args.out)
    preserved = len(rows)
    scraped = 0
    for label, content, kind in documents:
        codes = extract_codes_text(content) if kind == "text" else extract_codes(content)
        print(f"[parse] {label}: {len(codes)} event codes", file=sys.stderr)
        scraped += len(codes)
        rows.update(codes)

    if scraped == 0:
        print(
            "error: no event codes found in the supplied documents; "
            "the page layout may have changed or the fetch returned an error/bot-challenge page",
            file=sys.stderr,
        )
        return 1

    write_csv(args.out, rows)
    print(f"[write] {args.out}: {len(rows)} rows ({preserved} pre-existing before merge)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

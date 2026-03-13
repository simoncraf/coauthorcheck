from __future__ import annotations

import re

from coauthorcheck.models import Trailer

TRAILER_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9-]+: .+")


def extract_trailer_block(message: str) -> list[tuple[int, str]]:
    lines = message.splitlines()
    end = len(lines) - 1

    while end >= 0 and not lines[end].strip():
        end -= 1

    if end < 0:
        return []

    block: list[tuple[int, str]] = []
    found_trailer = False

    index = end
    while index >= 0:
        line = lines[index]

        if not line.strip():
            break

        is_continuation = bool(block) and line[:1].isspace()
        is_trailer = bool(TRAILER_TOKEN_PATTERN.match(line))

        if not found_trailer and not is_trailer:
            return []

        if is_trailer:
            found_trailer = True
            block.append((index + 1, line))
            index -= 1
            continue

        if is_continuation:
            block.append((index + 1, line))
            index -= 1
            continue

        break

    block.reverse()
    return block


def extract_trailers(message: str) -> list[Trailer]:
    trailers: list[Trailer] = []
    for line_number, line in extract_trailer_block(message):
        token, value = line.split(":", 1)
        trailers.append(
            Trailer(
                token=token.strip(),
                value=value.strip(),
                raw=line,
                line_number=line_number,
            )
        )
    return trailers


def extract_coauthor_trailers(message: str) -> list[Trailer]:
    return [
        trailer
        for trailer in extract_trailers(message)
        if trailer.token.lower() == "co-authored-by"
    ]
    
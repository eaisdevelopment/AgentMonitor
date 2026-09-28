"""Bounded native terminal surface; obsolete cursor redraws are overwritten."""

import re
import unicodedata

_CSI = re.compile(r"\x1b\[([0-?]*)([ -/]*)([@-~])")


def visible_terminal_lines_v1(
    text: str, *, height: int = 40, width: int = 160
) -> tuple[str, ...]:
    """Reconstruct only the current PTY surface, without retaining scrollback."""
    rows = [[" "] * width for _ in range(height)]
    row = column = 0
    saved = (0, 0)
    position = 0

    def linefeed() -> None:
        nonlocal row
        if row == height - 1:
            rows.pop(0)
            rows.append([" "] * width)
        else:
            row += 1

    while position < len(text):
        character = text[position]
        if character == "\x1b":
            match = _CSI.match(text, position)
            if match is None:
                selector = text[position : position + 2]
                if selector in {"\x1b7", "\x1b8"}:
                    if selector == "\x1b7":
                        saved = (row, column)
                    else:
                        row, column = saved
                    position += 2
                    continue
                # Native terminal character-set selection has no text cells.
                if text[position : position + 3] in {"\x1b(B", "\x1b)B"}:
                    position += 3
                    continue
                raise ValueError("usage_terminal_control_unsupported")
            parameters, _, command = match.groups()
            # Observed terminal/keyboard protocol controls do not change cells.
            if (parameters, command) in {
                (">0", "q"),
                ("?", "u"),
                (">4", "m"),
                ("<", "u"),
            }:
                position = match.end()
                continue
            if parameters.startswith("?"):
                if command not in {"h", "l"} or parameters not in {
                    "?25",
                    "?2004",
                    "?2031",
                    "?1004",
                    "?2026",
                }:
                    raise ValueError("usage_terminal_control_unsupported")
                position = match.end()
                continue
            values = [int(value) if value else 0 for value in parameters.split(";")]
            first = values[0]
            distance = first or 1
            if command == "A":
                row = max(0, row - distance)
            elif command == "B":
                row = min(height - 1, row + distance)
            elif command == "C":
                column = min(width - 1, column + distance)
            elif command == "D":
                column = max(0, column - distance)
            elif command in {"G", "`"}:
                column = min(width - 1, distance - 1)
            elif command == "d":
                row = min(height - 1, distance - 1)
            elif command in {"H", "f"}:
                row = min(height - 1, distance - 1)
                column = min(width - 1, (values[1] or 1) - 1) if len(values) > 1 else 0
            elif command in {"E", "F"}:
                row = max(
                    0,
                    min(height - 1, row + (distance if command == "E" else -distance)),
                )
                column = 0
            elif command == "K":
                if first not in {0, 1, 2}:
                    raise ValueError("usage_terminal_control_unsupported")
                erase_column = min(column, width - 1)
                start, end = (
                    (0, width)
                    if first == 2
                    else (
                        (0, erase_column + 1) if first == 1 else (erase_column, width)
                    )
                )
                rows[row][start:end] = [" "] * (end - start)
            elif command == "J":
                if first == 3:
                    pass  # Clear scrollback; this parser retains no scrollback.
                elif first == 2:
                    rows = [[" "] * width for _ in range(height)]
                elif first == 0:
                    rows[row][column:] = [" "] * (width - column)
                    for index in range(row + 1, height):
                        rows[index] = [" "] * width
                elif first == 1:
                    rows[row][: column + 1] = [" "] * (column + 1)
                    for index in range(row):
                        rows[index] = [" "] * width
                else:
                    raise ValueError("usage_terminal_control_unsupported")
            elif command == "s":
                saved = (row, column)
            elif command == "u":
                row, column = saved
            elif command == "r" and not parameters:
                row = column = 0  # Restore full-screen scroll region and home.
            elif command not in {"m", "h", "l", "n", "c", "q"}:
                raise ValueError("usage_terminal_control_unsupported")
            position = match.end()
            continue
        if character == "\r":
            column = 0
        elif character == "\n":
            linefeed()
        elif character == "\b":
            column = max(0, column - 1)
        elif character == "\t":
            column = min(width - 1, (column // 8 + 1) * 8)
        elif character.isprintable():
            if unicodedata.combining(character):
                if column:
                    rows[row][column - 1] += character
            else:
                size = 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
                if column + size > width:
                    column = 0
                    linefeed()
                rows[row][column] = character
                if size == 2:
                    rows[row][column + 1] = ""
                column += size
        position += 1
    return tuple(line for cells in rows if (line := "".join(cells).strip()))

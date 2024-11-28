from enum import Enum
from typing import Any

ANSI16_MARKER = 300
ANSI256_MARKER = 301
DEFAULT_MARKER = 302


class RgbColor(Enum):
    """
    A subset of CSS colors with RGB values that work well in Dark and Light mode.
    """

    TEAL = (0, 130, 128)
    OLIVEDRAB = (113, 122, 57)
    CHOCOLATE = (198, 77, 45)
    MEDIUMORCHID = (170, 74, 198)
    SEAGREEN = (49, 128, 125)
    SLATEBLUE = (127, 97, 206)
    DARKCYAN = (25, 128, 145)
    STEELBLUE = (51, 118, 193)
    MEDIUMPURPLE = (149, 82, 220)
    INDIANRED = (199, 74, 77)
    FORESTGREEN = (42, 134, 44)
    SLATEGRAY = (75, 123, 140)
    LIGHTSLATEGRAY = (125, 106, 170)
    MEDIUMSLATEBLUE = (100, 92, 255)
    GRAY = (144, 102, 146)
    DARKORCHID = (188, 36, 228)
    SIENNA = (178, 94, 30)
    OLIVE = (133, 116, 33)
    PALEVIOLETRED = (186, 77, 136)
    DARKGOLDENROD = (180, 93, 0)
    MEDIUMVIOLETRED = (212, 2, 184)
    BLUEVIOLET = (165, 50, 255)
    DIMGRAY = (95, 122, 115)
    DARKVIOLET = (202, 12, 211)
    DODGERBLUE = (0, 106, 255)
    DARKOLIVEGREEN = (88, 128, 41)

    @classmethod
    def get_by_name(cls: Any, name: str) -> "RgbColor":
        try:
            return cls[name.upper()]
        except KeyError as ex:
            msg = f"Color '{name}' is not a valid color name"
            raise ValueError(msg) from ex

    @classmethod
    def list_values(cls: Any) -> list[tuple[int, int, int]]:
        return [color.value for color in cls]


class AnsiColor(Enum):
    """Enum representing ANSI colors."""

    # Standard 16-bit colors
    BLACK = (ANSI16_MARKER, 0, 0)
    RED = (ANSI16_MARKER, 1, 0)
    GREEN = (ANSI16_MARKER, 2, 0)
    YELLOW = (ANSI16_MARKER, 3, 0)
    BLUE = (ANSI16_MARKER, 4, 0)
    MAGENTA = (ANSI16_MARKER, 5, 0)
    CYAN = (ANSI16_MARKER, 6, 0)
    WHITE = (ANSI16_MARKER, 7, 0)
    DEFAULT = (DEFAULT_MARKER, 9, 0)

    # Subset of 256-bit colors
    BRIGHT_BLACK = (ANSI256_MARKER, 8, 0)
    BRIGHT_RED = (ANSI256_MARKER, 9, 0)
    BRIGHT_GREEN = (ANSI256_MARKER, 10, 0)
    BRIGHT_YELLOW = (ANSI256_MARKER, 11, 0)
    BRIGHT_BLUE = (ANSI256_MARKER, 12, 0)
    BRIGHT_MAGENTA = (ANSI256_MARKER, 13, 0)
    BRIGHT_CYAN = (ANSI256_MARKER, 14, 0)
    BRIGHT_WHITE = (ANSI256_MARKER, 15, 0)


Color = AnsiColor | RgbColor


class ColorType(Enum):
    BG = 40
    FG = 30


def _join(*values: int | str) -> str:
    """
    Join a series of values with semicolons. The values
    are either integers or strings, so stringify each for
    good measure. Worth breaking out as its own function
    because semicolon-joined lists are core to ANSI coding.
    """
    return ";".join(str(v) for v in values)


def color_code(spec: tuple[int, int, int], base: ColorType) -> str:
    """
    Workhorse of encoding a color. Give preference to named colors from
    ANSI, then to specific numeric or tuple specs. If those don't work,
    try looking up CSS color names or parsing CSS color specifications
    (hex or rgb).
    """
    red = spec[0]
    green = spec[1]
    blue = spec[2]
    val = None
    if red == ANSI16_MARKER:
        val = _join(base.value + green)
    elif red == ANSI256_MARKER:
        val = _join(base.value + 8, 5, green)
    elif red == DEFAULT_MARKER:
        val = _join(base.value + 9)
    elif 0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255:
        val = _join(base.value + 8, 2, red, green, blue)
    else:
        msg = f"Invalid color specification: {spec}"
        raise ValueError(msg)

    return val


def color_by_tuple(
    message: str,
    fg: tuple[int, int, int] = AnsiColor.DEFAULT.value,
    bg: tuple[int, int, int] = AnsiColor.DEFAULT.value,
) -> str:
    codes: list[str] = []
    if fg[0] != DEFAULT_MARKER:
        codes.append(color_code(fg, ColorType.FG))

    if bg[0] != DEFAULT_MARKER:
        codes.append(color_code(bg, ColorType.BG))

    if codes:
        template = "\x1b[{0}m{1}\x1b[0m"
        return template.format(_join(*codes), message)
    return message


def color(
    message: str,
    fg: Color = AnsiColor.DEFAULT,
    bg: Color = AnsiColor.DEFAULT,
) -> str:
    """
    Add ANSI colors and styles to a string.
    """
    return color_by_tuple(message, fg.value, bg.value)


if __name__ == "__main__":
    print("====ANSI Colors====")
    for _, value in AnsiColor.__members__.items():
        print(color_by_tuple(f"{value}", fg=value.value))

    print("====CSS Colors====")
    for _, cs_value in RgbColor.__members__.items():
        print(color_by_tuple(f"{cs_value}", fg=cs_value.value))

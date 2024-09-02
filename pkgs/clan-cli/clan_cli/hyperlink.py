# Implementation of OSC8
def hyperlink(text: str, url: str) -> str:
    """
    Generate OSC8 escape sequence for hyperlinks.

    Args:
    url (str): The URL to link to.
    text (str): The text to display.

    Returns:
    str: The formatted string with an embedded hyperlink.
    """
    esc = "\033"
    return f"{esc}]8;;{url}{esc}\\{text}{esc}]8;;{esc}\\"


def hyperlink_same_text_and_url(url: str) -> str:
    """
    Keep the description and the link the same to support legacy terminals.
    """
    return hyperlink(url, url)


def help_hyperlink(description: str, url: str) -> str:
    import sys

    """
    Keep the description and the link the same to support legacy terminals.
    """
    if sys.argv[0].__contains__("docs.py"):
        return docs_hyperlink(description, url)

    return hyperlink_same_text_and_url(url)


def docs_hyperlink(description: str, url: str) -> str:
    """
    Returns a markdown hyperlink
    """
    return f"[{description}]({url})"

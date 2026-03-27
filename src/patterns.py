import re

DOI_REGEX = re.compile(
    r'(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',
    re.IGNORECASE,
)

UNWANTED_PATTERNS = [
    "Downloaded from",
    "by guest on",
    "©",
    re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)#,
    #DOI_REGEX
]

# TODO: handle scientific PDF artifacts (headers, footers, tables) before semantic chunking
import requests


def clean_filename_reference(filename: str) -> str:
    return (
        filename.replace("_", " ")
        .replace("-", " ")
        .replace(".pdf", "")
        .replace(".txt", "")
        .strip()
    )

def build_reference(item: dict):
    authors = item.get("author", [])

    first_author = "Unknown"
    if authors:
        family = authors[0].get("family", "")
        given = authors[0].get("given", "")
        initials = f"{given[0]}." if given else ""
        first_author = f"{family}, {initials}"

    year = (
        item.get("published-print", {}).get("date-parts", [[None]])[0][0]
        or item.get("published-online", {}).get("date-parts", [[None]])[0][0]
        or item.get("created", {}).get("date-parts", [[None]])[0][0]
    )

    title = item.get("title", [""])[0]

    journal = item.get("container-title", [""])
    journal = journal[0] if journal else ""

    volume = item.get("volume", "")
    issue = item.get("issue", "")

    doi = item.get("DOI", "")
    publisher = item.get("publisher", "")

    reference = (
        f"{first_author} ({year}). {title}. "
        f"{journal}"
    )

    if volume:
        reference += f", {volume}"

    if issue:
        reference += f"({issue})"

    if doi:
        reference += f". https://doi.org/{doi}"

    return {
        "reference": reference,
        "title": title,
        "journal": journal,
        "publisher": publisher,
        "doi": doi,
    }


def query_crossref_by_text(query: str, base_url: str):
    try:
        params = {
            "query.bibliographic": query,
            "rows": 1
        }

        r = requests.get(f"{base_url}/works", params=params, timeout=5)

        if r.status_code == 200:
            items = r.json()["message"]["items"]

            if items:
                return build_reference(items[0])

    except Exception as e:
        print(f"Crossref query error for '{query}': {e}")

    return None


def get_citation_from_crossref(
    doi: str = None,
    filename: str = None,
    query_title: str = None,
) -> dict:
    base_url = "https://api.crossref.org"

    # Fallback function for empty results
    def get_fallback():
        return {
            "reference": clean_filename_reference(filename) if filename else "Unknown Source",
            "title": "",
            "journal": None,
            "publisher": None,
            "doi": doi
        }

    # 1. DOI lookup
    if doi:
        try:
            r = requests.get(f"{base_url}/works/{doi}", timeout=5)
            if r.status_code == 200:
                item = r.json()["message"]
                return build_reference(item)

        except Exception as e:
            print(f"DOI lookup error: {e}")

    # 2. Filename query
    if filename:
        result = query_crossref_by_text(clean_filename_reference(filename), base_url)
        if result: return result

    # 3. Title query
    if query_title:
        result = query_crossref_by_text(query_title, base_url)
        if result: return result

    # 4. Fallback = filename
    return get_fallback()
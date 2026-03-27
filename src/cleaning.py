import re

# TODO: Refactor into a single regex pass; fix edge case where intentional
# dashes are merged (could be solved with a dictionary check).

def normalize_text(text: str) -> str:
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks
    text = re.sub(r"-\n(?=\w)", "", text)

    # Replace common spacing artifacts with regular spaces
    text = text.replace("\xa0", " ")  # NBSP = Non-Breaking Space
    text = text.replace("\u2002", " ")  # ENSP = En Space
    text = text.replace("\u2003", " ")  # EMSP = Em Space
    text = text.replace("\u2009", " ")  # THSP = Thin Space

    # Remove invisible / soft formatting artifacts
    text = text.replace("\u200b", "")  # ZWSP = Zero Width Space
    text = text.replace("\u00ad", "")  # SHY = Soft Hyphen

    # Remove control characters that are usually extraction noise
    text = text.replace("\x01", "")  # SOH = Start Of Heading
    text = text.replace("\x02", "")  # STX = Start Of Text
    text = text.replace("\x03", "")  # ETX = End Of Text
    text = text.replace("\x04", "")  # EOT = End Of Transmission

    # Clean each line without destroying paragraph structure
    cleaned_lines = []
    blank_count = 0

    for line in text.split("\n"):
        # Normalize spaces/tabs within the line
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()

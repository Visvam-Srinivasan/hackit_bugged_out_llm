import unicodedata
import re

def wash_text(text: str) -> str:
    # 1. Unicode Normalization (Fixes homoglyph attacks)
    text = unicodedata.normalize('NFKC', text)
    # 2. Invisible character removal
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    # 3. De-spacing logic (j a i l b r e a k -> jailbreak)
    if re.search(r'(?:[a-zA-Z]\s){3,}', text):
        text = re.sub(r'(?<=[a-zA-Z])\s(?=[a-zA-Z])', '', text)
    return text.strip()
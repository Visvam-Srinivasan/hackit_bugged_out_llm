# core/interceptor.py
import unicodedata
import re

def wash_text(text: str) -> str:
    """Layer 1: Adversarial Retokenizer"""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    if re.search(r'(?:[a-zA-Z]\s){3,}', text):
        text = re.sub(r'(?<=[a-zA-Z])\s(?=[a-zA-Z])', '', text)
    return text.strip()
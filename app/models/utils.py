import hashlib
from urllib.parse import urlparse, parse_qs, urlencode
from typing import List


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    filtered_params = {}
    for key, values in query_params.items():
        if key.lower() not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']:
            filtered_params[key] = values
    
    sorted_params = dict(sorted(filtered_params.items()))
    new_query = urlencode(sorted_params, doseq=True)
    
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if new_query:
        normalized += f"?{new_query}"
    
    return normalized


def generate_url_hash(url: str) -> str:
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def generate_title_hash(title: str) -> str:
    normalized_title = title.strip().lower()
    return hashlib.sha256(normalized_title.encode()).hexdigest()

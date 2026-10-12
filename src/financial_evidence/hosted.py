"""Fixed hosted transport destinations; original source identities stay separate."""
from urllib.parse import urlsplit

PLATFORM_URL = "https://agents.seiche.info"
SOURCE_DATASETS = {
    "https://api.seiche.info/api/v2/money-markets": "seiche.money_markets",
    "https://api.seiche.info/api/v2/world-markets?section=capital_markets": "seiche.capital_markets",
    "https://www.palimpsest.info/readings/china-index-latest.json": "palimpsest.china_index",
    "https://api.seiche.info/api/v2/world-markets?section=china_macro": "seiche.china_macro",
    "https://api.liquilens.in/api/failure-radar/board": "liquilens.failure_radar",
    "https://api.seiche.info/undertow/x402/summary": "undertow.summary",
    "https://api.seiche.info/api/v2/gift-city": "seiche.gift_city",
    "https://api.seiche.info/api/v2/world-markets?section=forex": "seiche.forex",
}


def platform_base(value=None):
    """Use the central service unless an operator explicitly chooses a test host."""
    value = PLATFORM_URL if value is None else value
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("platform URL must be an absolute HTTPS URL")
    parsed = urlsplit(value)
    if (parsed.scheme not in {"https", "http"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or ".." in parsed.path or "%" in parsed.path or "\\" in value
            or any(ord(char) < 33 or ord(char) == 127 for char in value)
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})):
        raise ValueError("platform URL requires HTTPS (or loopback) without credentials or unsafe paths")
    try:
        parsed.port
    except ValueError:
        raise ValueError("invalid platform port") from None
    return value.rstrip("/")


def source_endpoint(source_url):
    """Resolve only a reviewed source, never a caller-selected proxy target."""
    try:
        return PLATFORM_URL + "/v1/data/" + SOURCE_DATASETS[source_url]
    except (KeyError, TypeError):
        raise ValueError("source URL is outside the hosted dataset catalog") from None

from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

DATASETS = {'bank_risk', 'capital_markets', 'china_economy', 'market_liquidity',
            'money_market_history', 'money_markets', 'source_health'}
URL = 'https://api.seiche.info/openbb/api/v1/query'


def parameters(values: dict[str, Any]) -> dict[str, Any]:
    dataset = values.get('dataset', 'money_markets')
    entity = values.get('entity') or ''
    if dataset not in DATASETS or not isinstance(entity, str) or len(entity) > 100:
        raise ValueError('Use a listed dataset and an entity filter up to 100 characters.')
    result = {'dataset': dataset, 'entity': entity}
    for key, default, lower, upper in [('limit', 25, 1, 100), ('offset', 0, 0, 100000)]:
        value = values.get(key, default)
        if isinstance(value, bool):
            raise ValueError(f'{key} must be an integer from {lower} to {upper}.')
        try:
            integer = int(value)
        except (ValueError, TypeError, OverflowError):
            raise ValueError(f'{key} must be an integer from {lower} to {upper}.') from None
        if str(value) not in (str(integer), f'{integer}.0') or not lower <= integer <= upper:
            raise ValueError(f'{key} must be an integer from {lower} to {upper}.')
        result[key] = integer
    return result


def fetch_page(values: dict[str, Any]) -> dict[str, Any]:
    query = parameters(values)
    response = httpx.get(URL, params=query, timeout=30, follow_redirects=False,
                         headers={'Accept': 'application/json'})
    response.raise_for_status()
    data = response.json()
    if (not isinstance(data, dict) or data.get('schema') != 'liquidity-lab.openbb-table.v1'
            or data.get('dataset') != query['dataset']
            or not all(isinstance(data.get(key), list) for key in ('results', 'sources', 'diagnostics'))
            or 'next_offset' not in data):
        raise ValueError('Unexpected research response; no result was produced.')
    return data


class EvidencePageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield self.create_json_message(fetch_page(tool_parameters))

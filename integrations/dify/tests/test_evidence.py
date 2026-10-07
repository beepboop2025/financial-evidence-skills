import unittest
from unittest.mock import patch
import httpx
from tools.evidence_page import EvidencePageTool, URL, fetch_page, parameters

PAGE = {'schema': 'liquidity-lab.openbb-table.v1', 'dataset': 'bank_risk',
        'results': [{'value': None, 'as_of': None, 'availability': 'unavailable'}],
        'sources': [{'rights_status': 'unknown'}], 'diagnostics': [{'availability': 'restricted'}],
        'transport_status': 'partial', 'next_offset': 25}


class EvidenceTests(unittest.TestCase):
    def test_retains_partial_research_and_pagination(self):
        with patch('tools.evidence_page.httpx.get', return_value=httpx.Response(200, json=PAGE, request=httpx.Request('GET', URL))) as get:
            self.assertEqual(fetch_page({'dataset': 'bank_risk'}), PAGE)
            self.assertEqual(get.call_args.kwargs['params']['limit'], 25)
            self.assertFalse(get.call_args.kwargs['follow_redirects'])

    def test_invalid_inputs_do_not_make_requests(self):
        for values in [{'limit': 1.5}, {'offset': -1}, {'limit': True}, {'dataset': 'private'}, {'entity': 'x' * 101}]:
            with self.subTest(values=values), patch('tools.evidence_page.httpx.get') as get:
                with self.assertRaises(ValueError):
                    fetch_page(values)
                get.assert_not_called()

    def test_http_and_contract_errors_are_not_evidence(self):
        for status, body in [(503, PAGE), (200, {'error': 'down'}), (200, {**PAGE, 'dataset': 'money_markets'})]:
            with self.subTest(status=status, body=body), patch('tools.evidence_page.httpx.get', return_value=httpx.Response(status, json=body, request=httpx.Request('GET', URL))):
                with self.assertRaises((httpx.HTTPStatusError, ValueError)):
                    fetch_page({'dataset': 'bank_risk'})

    def test_dify_tool_emits_full_json_message(self):
        tool = EvidencePageTool.from_credentials({})
        with patch('tools.evidence_page.fetch_page', return_value=PAGE):
            messages = list(tool._invoke({'dataset': 'bank_risk'}))
        self.assertEqual(messages[0].message.json_object, PAGE)


if __name__ == '__main__':
    unittest.main()

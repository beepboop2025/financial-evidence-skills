"""Real REST boundary for optional, revocable research-installation measurement."""
import importlib.util
import tempfile
import unittest
from unittest.mock import patch

from financial_evidence import application_usage as usage
from financial_evidence.service import EvidenceService
from test_openbb_tables import MONEY, source_result


@unittest.skipUnless(all(importlib.util.find_spec(name) for name in ('fastapi','mcp','httpx')), 'workspace dependencies required')
class ResearchMeasurementTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from financial_evidence.workspace import create_app
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.service = EvidenceService(fetcher=lambda source, **kw: source_result(source, MONEY)); self.addCleanup(self.service.close)
        self.app = create_app(service=self.service, base_url='http://localhost:6900', usage_dir=self.tmp.name)
        self.client = TestClient(self.app, base_url='http://localhost:6900'); self.client.__enter__(); self.addCleanup(self.client.__exit__,None,None,None)

    def enroll(self, headers=None):
        response = self.client.post('/api/v1/applications', json={'measurement_consent':True}, headers=headers or {})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()

    def query(self, headers=None):
        return self.client.get('/api/v1/query?dataset=money_markets',headers=headers or {})

    def test_anonymous_reads_work_and_never_create_verified_people(self):
        self.assertEqual(self.query().status_code,200)
        report=usage.report(self.tmp.name)
        self.assertEqual(report['classes']['unverified']['applications_with_data_responses'],0)
        self.assertIsNone(report['downstream_users'])

    def test_consent_required_bounded_body_and_untrusted_origin_rejected(self):
        for body in [{},{'measurement_consent':False},{'measurement_consent':True,'email':'x'}]:
            self.assertEqual(self.client.post('/api/v1/applications',json=body).status_code,400)
        self.assertEqual(self.client.post('/api/v1/applications',content=b'x'*1025).status_code,413)
        self.assertEqual(self.client.post('/api/v1/applications',json={'measurement_consent':True},headers={'Origin':'https://evil.example'}).status_code,403)

    def test_same_installation_response_deduplicates_and_deletion_revokes_key(self):
        value=self.enroll(); headers={'Authorization':'Bearer '+value['token']}
        self.assertEqual(self.query(headers).headers['X-Financial-Evidence-Measurement'],'recorded')
        self.assertEqual(self.query(headers).headers['X-Financial-Evidence-Measurement'],'aggregate_or_duplicate')
        report=usage.report(self.tmp.name)
        self.assertEqual(report['classes']['unverified']['deduplicated_data_responses'],1)
        self.assertEqual(report['classes']['external_verified']['applications_with_data_responses'],0)
        self.assertIsNone(report['classes']['unverified']['retention']['7']['rate'])
        self.assertEqual(self.client.delete('/api/v1/applications/current',headers=headers).status_code,200)
        response=self.query(headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['X-Financial-Evidence-Measurement'],'invalid_measurement_key')
        self.assertEqual(usage.report(self.tmp.name)['classes']['unverified']['deduplicated_data_responses'],0)

    def test_operator_use_is_excluded_and_storage_failure_cannot_block_research(self):
        value=self.enroll({'X-Liquilens-Traffic-Class':'synthetic'})
        self.assertEqual(value['classification'],'internal')
        self.query({'Authorization':'Bearer '+value['token'],'X-Liquilens-Traffic-Class':'synthetic'})
        report=usage.report(self.tmp.name)
        self.assertEqual(report['classes']['synthetic']['applications_with_data_responses'],1)
        self.assertEqual(report['classes']['unverified']['applications_with_data_responses'],0)
        with patch.object(usage,'record',side_effect=OSError('unavailable')):
            result=self.query()
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.headers['X-Financial-Evidence-Measurement'],'unavailable')

    def test_browser_preflight_allows_public_desk_headers_and_rejects_foreign_origin(self):
        headers={'Origin':'https://beepboop2025.github.io','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization,x-liquilens-traffic-class'}
        result=self.client.options('/api/v1/query',headers=headers)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.headers['Access-Control-Allow-Origin'],headers['Origin'])
        self.assertEqual(self.client.options('/api/v1/query',headers={**headers,'Origin':'https://evil.example'}).status_code,400)

    def test_empty_results_and_diagnostic_views_do_not_start_a_cohort(self):
        value=self.enroll(); headers={'Authorization':'Bearer '+value['token']}
        result=self.client.get('/api/v1/query?dataset=money_markets&entity=nonexistent',headers=headers)
        self.assertEqual(result.headers['X-Financial-Evidence-Measurement'],'not_eligible')
        self.assertEqual(usage.report(self.tmp.name)['classes']['unverified']['applications_with_data_responses'],0)

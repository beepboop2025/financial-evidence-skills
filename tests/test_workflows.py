"""Boundary checks for source-preserving browser workflows and cohort attribution."""
import copy
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import date

from financial_evidence import workflows, application_usage as usage
from financial_evidence.service import EvidenceService
from test_openbb_tables import MONEY, source_result

MONITOR = {'schema':'liquilens.institution-monitoring.v1','rows':[{'slug':'au-sfb','current_metrics':3,'status':'insufficient_visibility','gaps':[{'field':'withdrawals'}]}], 'coverage_complete':False, 'score_authority':False}
EXIT = {'schema':'undertow.crypto-workbench.v1','status':'available','rungs':[{'published_size_usd':10000,'venues':[{'venue':'example','status':'available','sell_cost_bps':1.2}]}],'boundary':{'execution':False}}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.service = EvidenceService(fetcher=lambda source, **kw: source_result(source,MONEY))
        self.addCleanup(self.service.close)

    def test_selections_are_bounded_before_upstream_work(self):
        for workflow, selection in [('nope',''),('funding','USD?url=x'),('institutions','../x'),('institutions',','.join(['a']*6)),('exit','0'),('exit','NaN'),('exit','1000001'),('exit','1e4'),('exit','1,2,3,4,5')]:
            with self.subTest(workflow=workflow,selection=selection), self.assertRaises(ValueError):
                workflows.run(self.service,workflow,selection,fetcher=lambda *a,**k:self.fail('unexpected fetch'))
        self.assertEqual(workflows.selection_for('exit','10000.00,10000,0.10'),'10000,0.1')

    def test_source_evidence_is_retained_and_upstream_credentials_are_absent(self):
        calls=[]
        def fetch(url, *args, **kwargs): calls.append((url,args,kwargs)); return copy.deepcopy(MONITOR)
        result=workflows.run(self.service,'institutions','au-sfb',fetcher=fetch,synthetic=True)
        self.assertEqual(result['evidence'],MONITOR)
        self.assertTrue(result['prepared_response'])
        self.assertFalse(result['evidence']['coverage_complete'])
        self.assertEqual(calls[0][2],{'synthetic':True})
        result['evidence']['rows'][0]['current_metrics']=0
        self.assertFalse(workflows.prepared('institutions',result['evidence']))

    def test_exit_envelope_and_withheld_values(self):
        def fetch(url,**kwargs):
            self.assertEqual(url,workflows.EXIT_PUBLIC+'?sizes_usd=10000')
            return copy.deepcopy(EXIT)
        result=workflows.run(self.service,'exit','10000',fetcher=fetch)
        self.assertEqual(result['evidence'],EXIT)
        withheld=copy.deepcopy(EXIT); withheld['status']='unavailable'
        self.assertFalse(workflows.prepared('exit',withheld))
        for reply in [{'error':'unavailable'}, {'schema':'unexpected'}, []]:
            with self.assertRaises(ValueError): workflows.run(self.service,'exit',fetcher=lambda *a,**k:reply)

    def test_funding_uses_existing_sources_and_empty_results_never_qualify(self):
        value=workflows.run(self.service,'funding','USD')
        self.assertTrue(value['prepared_response'])
        self.assertEqual(value['evidence']['financial_authority'],'none')
        self.assertFalse(workflows.run(self.service,'funding','ZZZ')['prepared_response'])

    def test_workflow_return_cohorts_and_deletion(self):
        from financial_evidence.workspace_usage import report
        with tempfile.TemporaryDirectory() as root:
            with patch.object(usage,'day',return_value=date(2026,10,8)):
                enrolled=usage.enroll(root,{'measurement_consent':True},{})
                who=usage.identify(root,'Bearer '+enrolled['token'],{})
                usage.record(root,who,'a'*64,workflow='funding')
            with patch.object(usage,'day',return_value=date(2026,10,9)):
                usage.record(root,who,'a'*64,workflow='funding')
                usage.record(root,who,'b'*64,workflow='exit')
                value=report(root)
                self.assertEqual(value['workflows']['funding']['unverified']['returned_on_multiple_dates'],1)
                self.assertEqual(value['workflows']['exit']['unverified']['returned_on_multiple_dates'],0)
                self.assertIsNone(value['monthly_active_people'])
                self.assertEqual(value['workflows']['funding']['external_verified']['active'],0)
                usage.erase(root,who)
                self.assertEqual(report(root)['workflows']['funding']['unverified']['active'],0)

@unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('fastapi','mcp','httpx')),'workspace dependencies required')
class WorkflowRESTTests(unittest.TestCase):
    def test_real_route_errors_measurement_and_cors(self):
        from fastapi.testclient import TestClient
        from financial_evidence.workspace import create_app
        with tempfile.TemporaryDirectory() as root:
            service=EvidenceService(fetcher=lambda source,**kw:source_result(source,MONEY))
            self.addCleanup(service.close)
            with TestClient(create_app(service=service,base_url='http://localhost:6900',usage_dir=root),base_url='http://localhost:6900') as client:
                token=client.post('/api/v1/applications',json={'measurement_consent':True}).json()['token']
                headers={'Authorization':'Bearer '+token,'X-Liquilens-Traffic-Class':'synthetic','Origin':'https://beepboop2025.github.io'}
                response=client.get('/api/v1/workflow?workflow=funding&selection=USD',headers=headers)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers['X-Financial-Evidence-Measurement'],'recorded')
                self.assertEqual(response.headers['Access-Control-Allow-Origin'],headers['Origin'])
                self.assertEqual(response.headers['Cache-Control'],'no-store')
                self.assertEqual(client.get('/api/v1/workflow?workflow=exit&selection=0').status_code,422)
                with patch.object(workflows,'run',side_effect=ValueError('private upstream error')):
                    result=client.get('/api/v1/workflow?workflow=exit')
                    self.assertEqual(result.status_code,502)
                    self.assertNotIn('private',result.text)
                report=usage.report(root)
                self.assertEqual(report['classes']['synthetic']['applications_with_data_responses'],1)
                self.assertEqual(report['classes']['external_verified']['applications_with_data_responses'],0)

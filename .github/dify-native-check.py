import datetime
import hashlib
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

import yaml
from graphon.dsl import inspect, loads
from graphon.engine_events.graph import GraphRunSucceededEvent

root = pathlib.Path.cwd()
dsl = (root / 'docs/platforms/dify/first-evidence.yml').read_text()
record = json.loads((root / 'docs/distribution/dify-marketplace-archive-20261029.json').read_text())
identifier = record['marketplace_identifier']
signed_path = os.environ.get('SIGNED_PACKAGE')
if signed_path:
    package = pathlib.Path(signed_path).read_bytes()
else:
    request = urllib.request.Request(record['requested_url'] + '&cache=' + str(time.time_ns()), headers={'User-Agent': 'Dify-Workflow-Verification/1.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        package = response.read(16384)
assert hashlib.sha256(package).hexdigest() == record['sha256']
plan = inspect(dsl)
print('DSL load status:', plan.load_status, 'dependencies:', [dep.plugin_unique_identifier for dep in plan.dependencies], flush=True)
assert [dep.plugin_unique_identifier for dep in plan.dependencies] == [identifier]
with tempfile.TemporaryDirectory() as plugin_cache:
    target = pathlib.Path(plugin_cache) / identifier.replace(':', '-')
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        for path in archive.namelist():
            assert (target / path).resolve().is_relative_to(target.resolve())
        archive.extractall(target)
    creds = {'slim': {'plugin_folder': plugin_cache, 'uv_path': shutil.which('uv'), 'python_path': sys.executable, 'python_env_init_timeout': 300}}
    results = []
    for dataset, entity in [('money_markets','US-USD'),('market_liquidity','CRYPTO'),('bank_risk','au-sfb'),('money_markets',None),('money_markets','INVALID-PUBLIC-ID')]:
        inputs = {'dataset': dataset}
        if entity is not None:
            inputs['entity'] = entity
        engine = loads(dsl, workflow_id='financial-evidence-check', credentials=creds, start_inputs=inputs)
        events = list(engine.run())
        outcome = events[-1]
        for event in events:
            if type(event).__name__.endswith(('FailedEvent','PartialSucceededEvent')):
                print('FAILED', dataset, entity, event.model_dump(mode='json'), flush=True)
        assert isinstance(outcome, GraphRunSucceededEvent), (inputs, type(outcome).__name__, getattr(outcome,'error',None))
        pages = outcome.outputs['evidence']
        assert isinstance(pages,list) and len(pages) == 1, outcome.outputs
        page = pages[0]
        assert page['dataset'] == dataset and isinstance(page['sources'],list) and isinstance(page['diagnostics'],list)
        expected = 0 if entity == 'INVALID-PUBLIC-ID' else 1
        assert len(page['results']) == expected, (inputs,page['results'])
        if dataset == 'money_markets' and entity == 'US-USD':
            assert page['results'][0]['value'] is not None
        row = page['results'][0] if expected else {}
        result = {'inputs': inputs,'successful_nodes':[getattr(event,'node_id',None) for event in events if type(event).__name__ == 'NodeRunSucceededEvent'], 'result_count':len(page['results']),'observation':{key:row.get(key) for key in ['entity_id','metric','value','unit','as_of','availability','source_url']} if row else None,'sources':len(page['sources']),'diagnostics':len(page['diagnostics'])}
        print('CASE',json.dumps(result),flush=True)
        results.append(result)
print('NATIVE_RESULT',json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workflow_sha256':hashlib.sha256(dsl.encode()).hexdigest(),'signed_archive_sha256':record['sha256'],'inputs':results}),flush=True)

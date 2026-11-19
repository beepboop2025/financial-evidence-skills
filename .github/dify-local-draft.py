from app_factory import create_app
from core.db.session_factory import session_factory
from sqlalchemy import select
from models import Account, Tenant
from models.account import TenantAccountJoin
from models.model import App
from models.workflow import Workflow
from services.app_package_service import AppPackageService
from services.app_dsl_service import AppDslService, ImportMode, ImportStatus
_, app = create_app()
with app.app_context():
    with open('/tmp/first.ifpkg','rb') as stream:
        archive=AppPackageService().read_package(stream)
    assert archive is not None
    with session_factory.create_session() as session:
        account=Account(name='Owner acceptance',email='test@example.invalid')
        tenant=Tenant(name='Disposable verification workspace')
        session.add_all([account,tenant]);session.flush()
        session.add(TenantAccountJoin(tenant_id=tenant.id,account_id=account.id,role='owner'))
        session.flush()
        account.set_current_tenant_with_session(tenant,session=session)
        result=AppDslService(session).import_app(account=account,import_mode=ImportMode.YAML_CONTENT,yaml_content=archive.dsl,package=archive)
        print('DRAFT_IMPORT_STATUS',result.model_dump(mode='json'),flush=True)
        assert result.status in {ImportStatus.COMPLETED,ImportStatus.COMPLETED_WITH_WARNINGS},result
        app_id=result.app_id
        session.commit()
    with session_factory.create_session() as session:
        saved=session.scalar(select(App).where(App.id==app_id))
        draft=session.scalar(select(Workflow).where(Workflow.app_id==app_id,Workflow.version==Workflow.VERSION_DRAFT))
        assert saved.name == 'First financial evidence' and str(saved.mode)=='workflow'
        graph=draft.graph_dict
        assert [n['data']['type'] for n in graph['nodes']]==['start','tool','end']
        assert graph['nodes'][1]['data']['tool_name']=='evidence_page'
        print('DIFY_1_20_STORED_DRAFT',saved.name,'nodes',len(graph['nodes']),'edges',len(graph['edges']),flush=True)

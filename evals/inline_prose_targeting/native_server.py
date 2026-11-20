"""Loopback-only disposable proof adapter. No product route or provider dispatch."""
import argparse
from contextlib import asynccontextmanager
import os
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from application_state.errors import ApplicationStateError
from tests.application_state.conftest import _migrated_test_template, _cloned_test_database
from .native_fixture import NativeProseFixture
from .native_schema import extend_empty_clone


def create_app(root):
    @asynccontextmanager
    async def lifespan(app):
        admin = os.environ['DMB_APPLICATION_STATE_TEST_DATABASE_URL']
        parsed = urlparse(admin)
        if parsed.hostname != '127.0.0.1' or parsed.port != 55467 or parsed.path != '/postgres':
            raise RuntimeError('Proof adapter requires its uniquely owned loopback test server')
        with _migrated_test_template(admin) as template, _cloned_test_database(template) as dsn:
            extend_empty_clone(dsn,root/'test-only-schema.json')
            previous = os.environ.get('DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL')
            os.environ['DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL'] = dsn
            app.state.fixture = NativeProseFixture(root)
            try:
                yield
            finally:
                if previous is None: os.environ.pop('DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL',None)
                else: os.environ['DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL'] = previous
    app = FastAPI(lifespan=lifespan)
    @app.exception_handler(ApplicationStateError)
    async def state_error(_request, error): return JSONResponse({'error':str(error)},status_code=error.status_code)
    @app.exception_handler(ValueError)
    async def value_error(_request, error): return JSONResponse({'error':str(error)},status_code=422)
    @app.get('/health')
    def health(): return {'fixture':'synthetic-prose-only','provider_calls':0}
    @app.post('/bootstrap')
    async def bootstrap(request:Request): return app.state.fixture.bootstrap(await request.json())
    @app.post('/fixture')
    async def stage(request:Request): return app.state.fixture.stage(await request.json())
    @app.get('/page')
    def page(): return app.state.fixture.page()
    @app.get('/record/{action}')
    def record(action:str):
        from uuid import UUID
        fixture=app.state.fixture
        return fixture.proposals.get(fixture.world,UUID(action)).model_dump(mode='json')
    @app.get('/review/{action}')
    def read_review(action:str): return app.state.fixture.review(action)
    @app.post('/review/{action}')
    async def review(action:str,request:Request): return app.state.fixture.review(action,await request.json())
    @app.post('/save')
    async def save(request:Request): return app.state.fixture.save(await request.json())
    return app

if __name__ == '__main__':
    import uvicorn
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=15567);parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    if args.port != 15567: raise ValueError('This fixture owns only port15567')
    args.root.mkdir(parents=True,exist_ok=True)
    uvicorn.run(create_app(args.root),host='127.0.0.1',port=args.port,log_level='info')

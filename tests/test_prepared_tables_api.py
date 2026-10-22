from uuid import uuid4
from tests.test_world_play_run_content_api import api
from apps.live_control_server.routes.play_prepared_tables import router
from tests.application_state.test_prepared_table_receipts_postgres import setup, body
from tests.application_state.test_play_run_editions_postgres import WORLD


def test_native_auth_owner_and_command_validation(application_state_dsn,api):
    api.app.include_router(router)
    _,_,aggregate=setup();run_id=str(aggregate.run.run_id)
    path=f'/api/live/world-play-runs/v2/{run_id}/prepared-tables';params={'world_id':WORLD}
    headers={'Authorization':'Bearer synthetic-edition-operator-token-000000'}
    command=path+'/commands/'+str(uuid4());request=body(run_id).model_dump()
    assert api.get(path,params=params).status_code==401
    assert api.put(command,params=params,json=request).status_code==401
    assert api.get(path,params=params,headers=headers).status_code==200
    assert api.put(command,params=params,headers=headers,json={**request,'physical_value':True}).status_code==422
    assert api.put(command,params={'world_id':'other'},headers=headers,json=request).status_code==404
    first=api.put(command,params=params,headers=headers,json=request)
    assert first.status_code==200,first.text
    replay=api.put(command,params=params,headers=headers,json=request)
    assert replay.json()['receipt']==first.json()['receipt']
    assert replay.json()['replayed'] is True
    assert api.get(path+'/receipts',params=params,headers=headers).json()['receipts']==[first.json()['receipt']]

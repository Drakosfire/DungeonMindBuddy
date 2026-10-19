from uuid import uuid4
from tests.test_world_play_run_content_api import api
from tests.application_state.test_play_run_editions_postgres import create_source_run, WORLD
from tests.application_state.test_play_session_review_postgres import request


def test_authenticated_review_end_read_and_world_isolation(application_state_dsn,api):
    _,_,aggregate=create_source_run();run_id=str(aggregate.run.run_id)
    path=f"/api/live/world-play-runs/v2/{run_id}/review";params={"world_id":WORLD}
    headers={"Authorization":"Bearer synthetic-edition-operator-token-000000"}
    body=request(run_id).model_dump(mode="json");command=path+"/commands/"+str(uuid4())
    assert api.get(path,params=params).status_code==401
    assert api.put(command,params=params,json=body).status_code==401
    assert api.get(path,params=params,headers=headers).json()["review"] is None
    result=api.put(command,params=params,headers=headers,json=body)
    assert result.status_code==200,result.text
    assert api.get(path,params=params,headers=headers).json()["review"]==result.json()
    assert api.put(command,params={"world_id":"other"},headers=headers,json=body).status_code==404
    assert api.put(path+"/commands/"+str(uuid4()),params=params,headers=headers,json={**body,"extra":1}).status_code==422

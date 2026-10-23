import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {WorldSessionPreparation} from './WorldSessionPreparation';
const api=vi.hoisted(()=>({preview:vi.fn()}));vi.mock('./runEncountersApi',()=>({previewSession:api.preview}));afterEach(()=>{cleanup();vi.resetAllMocks();});
it('shows names and versions and requires explicit scene/encounter choices',async()=>{
 const source={playable_artifact_id:'doc-a',expected_playable_revision:2,expected_playable_work_revision_id:'rev-a',expected_playable_content_sha256:'a'.repeat(64)};
 const template={encounter_id:'template-a',revision:3,digest:'sha256:a'};
 const request={...source,schema_version:'dmb_world_session_create_v1',entry_scene_id:'scene:gate',encounters:[{scene_id:'scene:gate',template},{scene_id:'scene:landing',template:null}]};
 api.preview.mockResolvedValue({request,scenes:[{scene_id:'scene:gate',name:'The Gate',encounter_name:'Gate guardians',enemies:['Keeper'],template},{scene_id:'scene:landing',name:'The Landing',encounter_name:null,enemies:[],template:null}],excluded_orphan_count:1});
 const changed=vi.fn();render(<WorldSessionPreparation worldId="elderwyld" source={source} entrySceneId="scene:gate" onChange={changed}/>);
 await screen.findByText(/Gate guardians · version 3 · Keeper/);expect(screen.getByText(/links belong to scenes absent/)).toBeInTheDocument();
 fireEvent.click(screen.getByRole('checkbox'));expect(changed).toHaveBeenLastCalledWith({...request,encounters:[{scene_id:'scene:gate',template:null},{scene_id:'scene:landing',template:null}]});
 fireEvent.change(screen.getByRole('combobox'),{target:{value:'scene:landing'}});expect(changed.mock.lastCall?.[0].entry_scene_id).toBe('scene:landing');
});

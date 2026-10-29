from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from generationengine import GeneratedImage

from apps.live_control_server.routes import media_images

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


TOKEN = 'media-wizard-synthetic-operator-token-32chars'


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.delenv('DUNGEONBUDDY_FAL_KEY', raising=False)
    for name, value in {'DMB_AGENT_GRAPH_AUTH_MODE': 'local_operator', 'DMB_AGENT_GRAPH_AUTH_ENVIRONMENT': 'local', 'DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN': TOKEN, 'FAL_KEY': 'synthetic-never-sent'}.items():
        monkeypatch.setenv(name, value)
    client = SimpleNamespace(generate_image=AsyncMock(return_value=SimpleNamespace(images=[GeneratedImage(content=b'\x89PNG\r\n\x1a\n', media_type='image/png')], observation=SimpleNamespace(model_dump=lambda **kwargs: {'provider': 'fal', 'latency_ms': 10}))), aclose=AsyncMock())
    monkeypatch.setattr(media_images, '_image_client', lambda: client)
    monkeypatch.setattr(media_images, 'assert_at_head', lambda: None)
    monkeypatch.setattr(media_images.media, 'stage_image', lambda content, owner, provenance: {'asset_id': 'd3796b5d-d783-4195-b2cf-646debf276db', 'mime_type': 'image/png', 'state': 'staged'})
    app = FastAPI()
    app.include_router(media_images.router)
    return app, client


async def submit(setup, body, authenticated=True):
    app, _ = setup
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'} if authenticated else {}) as http:
        return await http.post('/api/live/media/images/generate', json=body)


async def test_generation_requires_operator_independent_of_graph(setup):
    result = await submit(setup, {'prompt': 'Edge', 'model': 'flux-2-pro'}, False)
    assert result.status_code == 401
    setup[1].generate_image.assert_not_called()


async def test_controls_and_image_round_trip(setup):
    result = await submit(setup, {'prompt': 'Edge', 'model': 'gpt-image-1.5', 'options': {'quality': 'low', 'background': 'transparent', 'output_format': 'png'}})
    assert result.status_code == 200
    assert result.headers['cache-control'] == 'no-store'
    assert result.json()['images'][0]['data_url'].startswith('data:image/png;base64,')
    request = setup[1].generate_image.call_args.args[0]
    assert request.options.quality == 'low' and request.options.background == 'transparent'
    setup[1].generate_image.assert_awaited_once()
    setup[1].aclose.assert_awaited_once()


@pytest.mark.parametrize('body', [{'prompt': 'x', 'model': 'bogus'}, {'prompt': 'x', 'model': 'flux-2-pro', 'options': {'quality': 'high'}}, {'prompt': 'x', 'model': 'gpt-image-1.5', 'width': 1536, 'height': 1536}, {'prompt': ' ', 'model': 'gpt-image-1.5'}])
async def test_invalid_requests_do_not_submit(setup, body):
    assert (await submit(setup, body)).status_code == 422
    setup[1].generate_image.assert_not_called()


async def test_missing_credential_does_not_submit(setup, monkeypatch):
    monkeypatch.delenv('FAL_KEY')
    assert (await submit(setup, {'prompt': 'Edge', 'model': 'flux-2-pro'})).status_code == 503
    setup[1].generate_image.assert_not_called()


@pytest.mark.parametrize(('dedicated', 'generic', 'expected'), [
    ('buddy-key', 'generic-key', 'buddy-key'),
    ('buddy-key', '', 'buddy-key'),
    ('  ', 'generic-key', 'generic-key'),
    ('', '', ''),
])
def test_dedicated_key_resolution(monkeypatch, dedicated, generic, expected):
    monkeypatch.setenv('DUNGEONBUDDY_FAL_KEY', dedicated)
    monkeypatch.setenv('FAL_KEY', generic)
    assert media_images._fal_key() == expected


def test_client_receives_dedicated_key(monkeypatch):
    monkeypatch.setenv('DUNGEONBUDDY_FAL_KEY', 'synthetic-buddy-key')
    provider = object()
    seen = {}
    def construct_provider(*, api_key):
        seen['key'] = api_key
        return provider
    monkeypatch.setattr(media_images, 'FalProvider', construct_provider)
    monkeypatch.setattr(media_images, 'GenerationClient', lambda *, image_provider: image_provider)
    assert media_images._image_client() is provider
    assert seen['key'] == 'synthetic-buddy-key'


async def test_dedicated_key_only_enables_capabilities_and_generation(setup, monkeypatch):
    monkeypatch.delenv('FAL_KEY')
    monkeypatch.setenv('DUNGEONBUDDY_FAL_KEY', 'synthetic-buddy-key')
    app, provider = setup
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'}) as http:
        response = await http.get('/api/live/media/images/capabilities')
        assert response.json()['configured'] is True
        assert 'synthetic-buddy-key' not in response.text
    assert (await submit(setup, {'prompt': 'Edge', 'model': 'flux-2-pro'})).status_code == 200
    provider.generate_image.assert_awaited_once()


async def test_library_setup_prevents_paid_generation(setup, monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    def unavailable():
        raise ApplicationStateUnavailableError('not migrated')
    monkeypatch.setattr(media_images, 'assert_at_head', unavailable)
    assert (await submit(setup, {'prompt': 'Edge', 'model': 'flux-2-pro'})).status_code == 503
    setup[1].generate_image.assert_not_called()


async def test_generation_stages_private_provenance_before_return(setup, monkeypatch):
    seen = []
    def stage(content, owner, provenance):
        seen.append((content, owner, provenance))
        return {'asset_id': 'd3796b5d-d783-4195-b2cf-646debf276db', 'mime_type': 'image/png', 'state': 'staged'}
    monkeypatch.setattr(media_images.media, 'stage_image', stage)
    response = await submit(setup, {'prompt': 'Edge private prompt', 'model': 'flux-2-pro'})
    assert response.status_code == 200
    assert len(seen) == 1 and seen[0][1]
    assert seen[0][2]['prompt'] == 'Edge private prompt'
    assert seen[0][2]['model'] == 'flux-2-pro'
    assert seen[0][2]['observation']['provider'] == 'fal'
    assert response.json()['images'][0]['state'] == 'staged'


async def test_owned_library_save_and_reopen_have_no_generation(setup, monkeypatch):
    from datetime import datetime, timezone
    from uuid import UUID
    aid = UUID('d3796b5d-d783-4195-b2cf-646debf276db')
    row = dict(asset_id=aid, created_at=datetime.now(timezone.utc), mime_type='image/png', width=3, height=2, byte_length=8,
               content_sha256='hash', provenance={'prompt': 'private'}, state='ready', owner_id='private-owner',
               fence='private-fence', receipt={'delivery_url': 'https://imagedelivery.net/synthetic/' + aid.hex + '/public'})
    owners = []
    def get(asset_id, owner):
        owners.append(owner)
        assert asset_id == aid
        return row
    monkeypatch.setattr(media_images.media, 'get_asset', get)
    monkeypatch.setattr(media_images.media, 'read_staged_bytes', lambda *args: b'original')
    monkeypatch.setattr(media_images.media, 'list_assets', lambda owner, **kwargs: owners.append(owner) or [row])
    save = AsyncMock(return_value=row)
    monkeypatch.setattr(media_images.media_storage, 'save_asset', save)
    app, provider = setup
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'}) as http:
        for path in ['library', str(aid)]:
            response = await http.get('/api/live/media/images/' + path)
            assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
            assert 'private-owner' not in response.text and 'private-fence' not in response.text
        assert (await http.get('/api/live/media/images/library?before_id=' + str(aid))).status_code == 422
        assert (await http.post('/api/live/media/images/' + str(aid) + '/save')).status_code == 200
    assert owners and all(owner == owners[0] for owner in owners)
    assert save.call_args.args == (aid, owners[0])
    provider.generate_image.assert_not_called()


async def test_image_metadata_does_not_read_original_bytes(setup, monkeypatch):
    from datetime import datetime, timezone
    from uuid import UUID

    aid = UUID("d3796b5d-d783-4195-b2cf-646debf276db")
    row = dict(
        asset_id=aid,
        created_at=datetime.now(timezone.utc),
        mime_type="image/png",
        width=3,
        height=2,
        byte_length=10,
        content_sha256="hash",
        provenance={},
        state="ready",
        receipt={
            "delivery_url": "https://imagedelivery.net/test/buddy-"
            + aid.hex
            + "/public"
        },
    )
    monkeypatch.setattr(media_images.media, "get_asset", lambda asset_id, owner: row)

    def no_bytes(*args, **kwargs):
        raise AssertionError("Metadata must not load original bytes")

    monkeypatch.setattr(media_images.media, "read_staged_bytes", no_bytes)
    app, _ = setup
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)),
        base_url="http://test",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ) as http:
        response = await http.get("/api/live/media/images/" + str(aid) + "/metadata")
    assert response.status_code == 200 and "data_url" not in response.json()


async def test_catalog_auth_paging_and_selection_do_not_generate(setup):
    from datetime import datetime, timezone
    from generationengine import ProviderCatalogModel, ProviderCatalogPage
    app, provider = setup
    provider.list_image_models = AsyncMock(return_value=ProviderCatalogPage(
        provider='fal', models=[
            ProviderCatalogModel(endpoint_id='bytedance/seedream/v5/pro/text-to-image', executable_model='seedream-v5-pro', metadata={'display_name': 'Seedream'}),
            ProviderCatalogModel(endpoint_id='future/model', metadata={'display_name': 'Future'}),
        ], has_more=True, next_cursor='next', fetched_at=datetime.now(timezone.utc),
    ))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test') as http:
        assert (await http.get('/api/live/media/images/catalog')).status_code == 401
        provider.list_image_models.assert_not_called()
        response = await http.get('/api/live/media/images/catalog?cursor=old&limit=7', headers={'Authorization': f'Bearer {TOKEN}'})
    assert response.status_code == 200 and response.headers['cache-control'] == 'no-store'
    body = response.json()
    assert body['next_cursor'] == 'next' and body['has_more']
    assert [item['selectable'] for item in body['models']] == [True, False]
    provider.list_image_models.assert_awaited_once_with(category='text-to-image', cursor='old', limit=7)
    provider.generate_image.assert_not_called()
    provider.aclose.assert_awaited_once()


async def test_catalog_failure_is_visible_and_does_not_generate(setup):
    from generationengine import FailureCode, GenerationEngineError, InferenceFailure
    app, provider = setup
    provider.list_image_models = AsyncMock(side_effect=GenerationEngineError(
        InferenceFailure.from_code(FailureCode.PROVIDER_UNAVAILABLE), SimpleNamespace(),
    ))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'}) as http:
        response = await http.get('/api/live/media/images/catalog')
    assert response.status_code == 502
    assert 'selection is unchanged' in response.json()['detail']['message']
    provider.generate_image.assert_not_called()
    provider.aclose.assert_awaited_once()


@pytest.mark.parametrize(('model', 'options'), [
    ('gpt-image-2.5-flare', {'quality': 'high', 'background': 'auto'}),
    ('gpt-image-2.5-sunburst', {'quality': 'medium'}),
    ('seedream-v5-pro', {'output_format': 'jpeg'}),
    ('nano-banana-2-lite', {'seed': 0, 'output_format': 'webp'}),
])
async def test_operator_selected_models_forward_supported_controls(setup, model, options):
    response = await submit(setup, {'prompt': 'Edge map', 'model': model, 'options': options})
    assert response.status_code == 200
    request = setup[1].generate_image.call_args.args[0]
    assert request.model == model
    assert request.options.model_dump(exclude_none=True) == options


@pytest.mark.parametrize(('model', 'options'), [
    ('seedream-v5-pro', {'seed': 0}), ('seedream-v5-pro', {'output_format': 'webp'}),
    ('nano-banana-2-lite', {'quality': 'high'}),
])
async def test_selected_models_reject_inapplicable_controls(setup, model, options):
    assert (await submit(setup, {'prompt': 'Edge', 'model': model, 'options': options})).status_code == 422
    setup[1].generate_image.assert_not_called()


async def test_capabilities_curate_exact_four_without_catalog_call(setup):
    app, provider = setup
    provider.list_image_models = AsyncMock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)), base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'}) as http:
        body = (await http.get('/api/live/media/images/capabilities')).json()
    assert body['default_model_id'] == 'gpt-image-2.5-flare'
    assert {item['id'] for item in body['models']} == {'gpt-image-2.5-flare','gpt-image-2.5-sunburst','seedream-v5-pro','nano-banana-2-lite'}
    provider.list_image_models.assert_not_called()


async def test_map_purpose_has_exact_effective_prompt_and_preserves_authored_provenance(setup, monkeypatch):
    seen=[]
    def stage(content, owner, provenance):
        seen.append(provenance)
        return {'asset_id':'d3796b5d-d783-4195-b2cf-646debf276db','mime_type':'image/png','state':'staged'}
    monkeypatch.setattr(media_images.media,'stage_image',stage)
    response=await submit(setup,{'prompt':'Edge, the old fort and swamp','model':'gpt-image-2.5-flare','purpose':'map'})
    assert response.status_code==200
    expected=media_images.MAP_FRAMING+'\n\nEdge, the old fort and swamp'
    assert setup[1].generate_image.call_args.args[0].prompt==expected
    assert response.json()['prompt']==expected
    assert seen[0]['prompt']==expected and seen[0]['authored_prompt']=='Edge, the old fort and swamp'
    assert seen[0]['settings']['purpose']=='map'


async def test_prepared_generation_passes_real_storage_json_admission(setup, monkeypatch):
    """An agent preparation ID must survive the real pre-DB provenance validation."""
    import io
    from uuid import UUID
    from PIL import Image
    from application_state import media

    aid = UUID('d3796b5d-d783-4195-b2cf-646debf276db')
    preparation_id = UUID('b8170e50-9b5f-4f34-9557-5bd20cd5db1b')
    monkeypatch.setattr(media_images.BuildImageService, 'get', lambda *args:
                        SimpleNamespace(model_dump=lambda **kwargs: {'action_id': str(preparation_id)}))
    content = io.BytesIO()
    Image.new('RGB', (2, 2)).save(content, format='PNG')
    setup[1].generate_image.return_value.images = [GeneratedImage(content=content.getvalue(), media_type='image/png')]
    import importlib.util
    spec = importlib.util.spec_from_file_location('media_admission_witness', media.__file__)
    admission = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admission)
    real_stage = admission.stage_image
    seen = []

    class ReachedDatabase(Exception):
        pass

    def database_boundary(*args, **kwargs):
        raise ReachedDatabase()

    monkeypatch.setattr(admission, 'unit_of_work', database_boundary)
    from application_state.errors import ApplicationStateValidationError
    with pytest.raises(ApplicationStateValidationError, match='JSON-safe'):
        real_stage(content.getvalue(), 'synthetic-owner', {'settings': {'preparation_id': preparation_id}})

    def stage(content, owner, provenance):
        with pytest.raises(ReachedDatabase):
            real_stage(content, owner, provenance)
        seen.append(provenance)
        return {'asset_id': aid, 'mime_type': 'image/png', 'state': 'staged'}

    monkeypatch.setattr(media_images.media, 'stage_image', stage)
    response = await submit(setup, {'prompt': 'Edge map', 'model': 'gpt-image-2.5-flare',
                                   'purpose': 'map', 'preparation_id': str(preparation_id)})
    assert response.status_code == 200
    assert seen[0]['settings']['preparation_id'] == str(preparation_id)
    assert response.json()['settings']['preparation_id'] == str(preparation_id)
    setup[1].generate_image.assert_awaited_once()


PARENT = 'ac6c15cc-8c68-4732-8ae2-d9f3f051393a'
CHILD = 'bc6c15cc-8c68-4732-8ae2-d9f3f051393a'


@pytest.fixture
def contextual(setup, monkeypatch):
    import hashlib
    content = b'retained-original'
    parent = {'asset_id': PARENT, 'state': 'staged', 'mime_type': 'image/png', 'width': 1536,
              'height': 1024, 'content_sha256': hashlib.sha256(content).hexdigest()}
    monkeypatch.setattr(media_images.media, 'get_asset', lambda *_: parent)
    monkeypatch.setattr(media_images.media, 'read_staged_bytes', lambda *_: content)
    setup[1].edit_image = AsyncMock(return_value=setup[1].generate_image.return_value)
    staged = []
    def stage(data, owner, provenance):
        staged.append((data, owner, provenance))
        return {'asset_id': CHILD, 'state': 'staged'}
    monkeypatch.setattr(media_images.media, 'stage_image', stage)
    return setup, parent, content, staged


async def regenerate(contextual, changes=None, authenticated=True):
    (app, _), parent, _, _ = contextual
    body = {'mode': 'image_to_image', 'instructions': 'Keep the retreat path clear.',
            'expected_content_sha256': parent['content_sha256']} | (changes or {})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=('127.0.0.1', 1234)),
        base_url='http://test', headers={'Authorization': f'Bearer {TOKEN}'} if authenticated else {}) as http:
        return await http.post(f'/api/live/media/images/{PARENT}/regenerate', json=body)


@pytest.mark.parametrize('mode', ['image_to_image', 'new'])
async def test_contextual_generation_retains_immutable_child_and_correct_input(contextual, mode):
    import base64
    setup, parent, original, staged = contextual
    result = await regenerate(contextual, {'mode': mode})
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    assert result.json()['asset_id'] == CHILD and result.json()['parent_asset_id'] == PARENT
    called = setup[1].edit_image if mode == 'image_to_image' else setup[1].generate_image
    other = setup[1].generate_image if mode == 'image_to_image' else setup[1].edit_image
    called.assert_awaited_once(); other.assert_not_awaited()
    request = called.call_args.args[0]
    assert request.prompt == 'Keep the retreat path clear.'
    assert request.source_image_url is None
    assert request.base_image_base64 == ('data:image/png;base64,' + base64.b64encode(original).decode() if mode == 'image_to_image' else None)
    assert request.model == ('flux-2-pro' if mode == 'image_to_image' else 'gpt-image-2.5-flare')
    assert len(staged) == 1 and staged[0][1] == 'local_operator'
    provenance = staged[0][2]
    assert provenance['parent_asset_id'] == PARENT and provenance['parent_content_sha256'] == parent['content_sha256']
    assert provenance['mode'] == mode and provenance['instructions'] == request.prompt
    assert parent['state'] == 'staged' and 'base_image_base64' not in provenance
    setup[1].aclose.assert_awaited_once()


async def test_contextual_generation_requires_auth_before_asset_or_provider(contextual, monkeypatch):
    def forbidden(*_):
        pytest.fail('Asset read before authorization')
    monkeypatch.setattr(media_images.media, 'get_asset', forbidden)
    assert (await regenerate(contextual, authenticated=False)).status_code == 401
    contextual[0][1].edit_image.assert_not_awaited()


@pytest.mark.parametrize('state', ['uploading', 'unknown'])
async def test_contextual_generation_rejects_unready_source(contextual, state):
    contextual[1]['state'] = state
    assert (await regenerate(contextual)).status_code == 409
    contextual[0][1].edit_image.assert_not_awaited()


async def test_contextual_generation_rejects_hash_drift_before_provider(contextual):
    assert (await regenerate(contextual, {'expected_content_sha256': 'b'*64})).status_code == 409
    contextual[0][1].edit_image.assert_not_awaited()


@pytest.mark.parametrize('failure', ['foreign', 'corrupt'])
async def test_contextual_generation_rejects_unowned_or_corrupt_source(contextual, monkeypatch, failure):
    from application_state.errors import ApplicationStateNotFoundError, ApplicationStateIntegrityError
    def refuse(*_):
        raise (ApplicationStateNotFoundError('Unavailable') if failure == 'foreign' else ApplicationStateIntegrityError('Corrupt'))
    monkeypatch.setattr(media_images.media, 'get_asset' if failure == 'foreign' else 'read_staged_bytes', refuse)
    assert (await regenerate(contextual)).status_code in {404, 409, 500}
    contextual[0][1].edit_image.assert_not_awaited()


@pytest.mark.parametrize('changes', [{'instructions': ' '}, {'mode': 'fake'}, {'owner': 'foreign'}, {'source_image_url': 'https://foreign.test/image'}, {'model': 'unselected'}])
async def test_contextual_generation_rejects_untrusted_request_fields(contextual, changes):
    assert (await regenerate(contextual, changes)).status_code == 422
    contextual[0][1].edit_image.assert_not_awaited()

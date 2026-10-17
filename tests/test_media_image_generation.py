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

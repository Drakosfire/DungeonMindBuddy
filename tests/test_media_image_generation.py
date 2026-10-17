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
    for name, value in {'DMB_AGENT_GRAPH_AUTH_MODE': 'local_operator', 'DMB_AGENT_GRAPH_AUTH_ENVIRONMENT': 'local', 'DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN': TOKEN, 'FAL_KEY': 'synthetic-never-sent'}.items():
        monkeypatch.setenv(name, value)
    client = SimpleNamespace(generate_image=AsyncMock(return_value=SimpleNamespace(images=[GeneratedImage(content=b'\x89PNG\r\n\x1a\n', media_type='image/png')], observation=SimpleNamespace(model_dump=lambda **kwargs: {'provider': 'fal', 'latency_ms': 10}))), aclose=AsyncMock())
    monkeypatch.setattr(media_images.GenerationClient, 'from_env', lambda: client)
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

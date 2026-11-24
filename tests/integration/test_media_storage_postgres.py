"""Real APP persistence with synthetic Cloudflare transport; no paid generation."""
import asyncio
import io

import httpx
import pytest
from fastapi import HTTPException
from PIL import Image

from application_state import media
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from apps.live_control_server.services import media_storage


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
def database(application_state_dsn):
    return application_state_dsn



@pytest.fixture
def asset(database, monkeypatch):
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'a' * 32)
    monkeypatch.setenv('CLOUDFLARE_IMAGES_API_TOKEN', 'synthetic-token')
    content = io.BytesIO()
    Image.new('RGB', (3, 2), 'green').save(content, format='PNG')
    return media.stage_image(content.getvalue(), 'owner-a', {'prompt': 'private swamp', 'model': 'synthetic'}, dsn=database)


def provider_result(row):
    return {'success': True, 'result': {'id': 'buddy-' + row['asset_id'].hex, 'meta': media_storage._metadata(row), 'requireSignedURLs': False,
                                      'variants': ['https://imagedelivery.net/synthetic/buddy-' + row['asset_id'].hex + '/public']}}


@pytest.mark.anyio
async def test_revocation_during_cdn_lookup_releases_claim_without_upload(database, asset):
    calls = []
    revoked = False

    def transport(request):
        nonlocal revoked
        calls.append(request.method)
        revoked = True
        return httpx.Response(404)

    def authorize_write():
        if revoked:
            raise HTTPException(403)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(HTTPException) as denied:
            await media_storage.save_asset(
                asset["asset_id"], "owner-a", dsn=database, client=client, authorize_write=authorize_write,
            )
    assert denied.value.status_code == 403
    assert calls == ["GET"]
    assert media.get_asset(asset["asset_id"], "owner-a", dsn=database)["state"] == "staged"


@pytest.mark.anyio
async def test_upload_verified_before_ready_and_reopens_without_upload(database, asset):
    calls = []
    uploaded = False
    def transport(request):
        nonlocal uploaded
        calls.append(request.method)
        if request.method == 'POST':
            assert b'private swamp' not in request.content and b'owner-a' not in request.content
            assert ('buddy-' + asset['asset_id'].hex).encode() in request.content
            assert str(request.url).endswith('/images/v1')
            assert media.get_asset(asset['asset_id'], 'owner-a', dsn=database)['state'] == 'uploading'
            uploaded = True
        return httpx.Response(200, json=provider_result(asset)) if uploaded else httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        assert result['state'] == 'ready' and calls == ['GET', 'POST', 'GET']
        assert media.get_asset(asset['asset_id'], 'owner-a', dsn=database)['receipt'] == result['receipt']
        assert media.read_staged_bytes(asset['asset_id'], 'owner-a', dsn=database)
        await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        assert calls == ['GET', 'POST', 'GET']


@pytest.mark.anyio
async def test_timeout_reconciles_exact_object_without_reposting(database, asset):
    calls = []
    uploaded = False
    def transport(request):
        nonlocal uploaded
        calls.append(request.method)
        if request.method == 'POST':
            uploaded = True
            raise httpx.ReadTimeout('unknown outcome')
        return httpx.Response(200, json=provider_result(asset)) if uploaded else httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(media_storage.MediaStorageUnavailable):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        assert media.get_asset(asset['asset_id'], 'owner-a', dsn=database)['state'] == 'unknown'
        result = await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        assert result['state'] == 'ready' and calls == ['GET', 'POST', 'GET']


@pytest.mark.anyio
async def test_unknown_missing_object_never_blindly_posts(database, asset):
    media.claim_upload(asset['asset_id'], 'owner-a', dsn=database)
    calls = []
    def transport(request):
        calls.append(request.method)
        return httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(ApplicationStateConflictError):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
    assert calls == ['GET']


@pytest.mark.anyio
async def test_known_rejection_preserves_original_and_allows_corrected_save(database, asset):
    calls = []
    def transport(request):
        calls.append(request.method)
        return httpx.Response(403) if request.method == 'POST' else httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(media_storage.MediaStorageUnavailable):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
    assert calls == ['GET', 'POST']
    assert media.get_asset(asset['asset_id'], 'owner-a', dsn=database)['state'] == 'staged'
    assert media.read_staged_bytes(asset['asset_id'], 'owner-a', dsn=database)


@pytest.mark.anyio
async def test_collision_does_not_upload_or_claim_success(database, asset):
    body = provider_result(asset)
    body['result']['meta']['content_sha256'] = 'wrong'
    calls = []
    def transport(request):
        calls.append(request.method)
        return httpx.Response(200, json=body)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        with pytest.raises(ApplicationStateIntegrityError):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
    assert calls == ['GET'] and media.get_asset(asset['asset_id'], 'owner-a', dsn=database)['state'] != 'ready'


@pytest.mark.anyio
async def test_concurrent_save_has_one_upload(database, asset):
    entered = asyncio.Event()
    release = asyncio.Event()
    uploaded = False
    posts = []
    async def transport(request):
        nonlocal uploaded
        if request.method == 'POST':
            posts.append(request)
            entered.set()
            await release.wait()
            uploaded = True
        return httpx.Response(200, json=provider_result(asset)) if uploaded else httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        first = asyncio.create_task(media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client))
        await asyncio.wait_for(entered.wait(), 5)
        with pytest.raises(ApplicationStateConflictError):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        release.set()
        assert (await first)['state'] == 'ready'
    assert len(posts) == 1


@pytest.mark.anyio
async def test_crash_after_upload_before_app_ack_reconciles(database, asset, monkeypatch):
    original = media.complete_upload
    uploaded = False
    posts = 0
    def transport(request):
        nonlocal uploaded, posts
        if request.method == 'POST':
            posts += 1
            uploaded = True
        return httpx.Response(200, json=provider_result(asset)) if uploaded else httpx.Response(404)
    def crash(*args, **kwargs):
        raise RuntimeError('APP unavailable after upload')
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        monkeypatch.setattr(media, 'complete_upload', crash)
        with pytest.raises(media_storage.MediaStorageUnavailable):
            await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client)
        monkeypatch.setattr(media, 'complete_upload', original)
        assert (await media_storage.save_asset(asset['asset_id'], 'owner-a', dsn=database, client=client))['state'] == 'ready'
    assert posts == 1


def test_uuid_shaped_provider_identity_is_rejected(asset):
    body = provider_result(asset)
    body['result']['id'] = asset['asset_id'].hex
    response = httpx.Response(200, json=body, request=httpx.Request('GET', 'https://api.cloudflare.com/synthetic'))
    with pytest.raises(ApplicationStateIntegrityError):
        media_storage._verified_receipt(response, asset, 'a' * 32)

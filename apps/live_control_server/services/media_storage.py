"""Public Cloudflare delivery for Buddy-owned immutable media candidates."""
from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from application_state import media
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError, ApplicationStateUnavailableError


class MediaStorageUnavailable(ApplicationStateUnavailableError):
    pass


def _configuration() -> tuple[str, str]:
    account = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '').strip()
    token = os.environ.get('CLOUDFLARE_IMAGES_API_TOKEN', '').strip()
    if not re.fullmatch(r'[a-fA-F0-9]{32}', account) or not token:
        raise MediaStorageUnavailable('Image CDN storage is not configured.')
    return account, token


def configured() -> bool:
    try:
        _configuration()
        return True
    except MediaStorageUnavailable:
        return False


def _metadata(row: dict) -> dict[str, str]:
    return {'asset_id': str(row['asset_id']), 'content_sha256': row['content_sha256'],
            'provenance_sha256': row['provenance_sha256'],
            'owner_sha256': hashlib.sha256(row['owner_id'].encode()).hexdigest()}


def _verified_receipt(response: httpx.Response, row: dict, account: str) -> dict:
    response.raise_for_status()
    body = response.json()
    result = body.get('result')
    expected_id = row['asset_id'].hex
    if body.get('success') is not True or not isinstance(result, dict):
        raise ApplicationStateIntegrityError('Image CDN returned no verifiable asset.')
    if result.get('id') != expected_id or result.get('meta') != _metadata(row) or result.get('requireSignedURLs') is not False:
        raise ApplicationStateIntegrityError('Image CDN identity or provenance did not match this asset.')
    delivery = None
    for url in result.get('variants', []):
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        parts = parsed.path.strip('/').split('/')
        if parsed.scheme == 'https' and parsed.netloc == 'imagedelivery.net' and not parsed.query and not parsed.fragment and len(parts) == 3 and parts[1] == expected_id and parts[2] == 'public':
            delivery = url
            break
    if delivery is None:
        raise ApplicationStateIntegrityError('Image CDN did not return a verified public delivery address.')
    return {'backend': 'cloudflare_images', 'account_id': account, 'object_id': expected_id,
            'original_sha256': row['content_sha256'], 'provenance_sha256': row['provenance_sha256'],
            'owner_id': row['owner_id'], 'asset_id': str(row['asset_id']), 'visibility': 'public', 'delivery_url': delivery}


async def save_asset(asset_id: str | UUID, owner: str, *, dsn: str | None = None, client: httpx.AsyncClient | None = None) -> dict:
    row = media.get_asset(asset_id, owner, dsn=dsn)
    if row['state'] == 'ready':
        return row
    account, token = _configuration()
    content = media.read_staged_bytes(asset_id, owner, dsn=dsn)
    if client is None:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False) as owned:
            return await save_asset(asset_id, owner, dsn=dsn, client=owned)
    started = row['state'] == 'staged'
    fence = media.claim_upload(asset_id, owner, dsn=dsn) if started else row['fence']
    # A provider I/O operation never runs inside an APP transaction.
    endpoint = f'https://api.cloudflare.com/client/v4/accounts/{account}/images/v1'
    object_url = endpoint + '/' + row['asset_id'].hex
    headers = {'Authorization': 'Bearer ' + token}
    post_started = False
    released = False
    try:
        found = await client.get(object_url, headers=headers)
        if found.status_code == 404:
            if not started:
                raise ApplicationStateConflictError('Upload is pending or its outcome is unknown. Check Save status again; this will not regenerate the image.')
            post_started = True
            extension = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}[row['mime_type']]
            uploaded = await client.post(endpoint, headers=headers,
                data={'id': row['asset_id'].hex, 'metadata': json.dumps(_metadata(row)), 'requireSignedURLs': 'false'},
                files={'file': (f"{row['asset_id']}.{extension}", content, row['mime_type'])})
            if uploaded.status_code in {400, 401, 403, 413, 415, 422}:
                media.mark_upload_rejected(asset_id, owner, fence, dsn=dsn)
                released = True
                raise MediaStorageUnavailable('The CDN rejected this save. Your original image is retained; correct storage setup and retry Save.')
            _verified_receipt(uploaded, row, account)
            # A returned POST alone is not a durable Save receipt.
            found = await client.get(object_url, headers=headers)
        verified = _verified_receipt(found, row, account)
        return media.complete_upload(asset_id, owner, fence, verified, dsn=dsn)
    except ApplicationStateConflictError:
        raise
    except Exception as error:
        if started and not released:
            if post_started:
                media.mark_upload_unknown(asset_id, owner, fence, dsn=dsn)
            else:
                media.mark_upload_rejected(asset_id, owner, fence, dsn=dsn)
        if isinstance(error, (ApplicationStateIntegrityError, MediaStorageUnavailable)):
            raise
        raise MediaStorageUnavailable('The CDN save could not be confirmed. Your original image is retained; check Save status before trying again.') from error

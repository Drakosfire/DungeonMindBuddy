"""Hosted artwork owner lookup must not stall unrelated async requests."""

import asyncio
from threading import Event
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from apps.live_control_server.services import hosted_native_graph_access as access


def request():
    return SimpleNamespace(
        state=SimpleNamespace(hosted_route_asset_id=str(uuid4())),
        query_params={},
        method="GET",
        body=_empty_body,
    )


async def _empty_body():
    return b""


class TestHostedArtworkNonblocking(TestCase):
    def test_slow_owner_lookup_does_not_block_other_requests(self):
        entered = Event()
        release = Event()
        timed_out = Event()

        def slow_candidates(subject):
            self.assertEqual(subject, "owner")
            entered.set()
            if not release.wait(timeout=2):
                timed_out.set()
            return frozenset({"world"})

        async def exercise():
            async def unrelated_request():
                # Yield until the resolver starts its candidate lookup.
                while not entered.is_set():
                    await asyncio.sleep(0.001)
                stalled = timed_out.is_set()
                release.set()
                return stalled

            pending = asyncio.create_task(access.resolve_hosted_saved_artwork(req))
            try:
                stalled = await asyncio.wait_for(unrelated_request(), timeout=3)
                self.assertFalse(stalled, "owner lookup blocked the event loop")
                self.assertEqual(await pending, "world")
                self.assertEqual(req.state.hosted_saved_artwork, (req.state.hosted_route_asset_id, "world"))
            finally:
                release.set()
                await asyncio.gather(pending, return_exceptions=True)

        req = request()
        with (
            patch.object(access, "_hosted_subject", return_value="owner"),
            patch.object(access, "_owner_world_candidates", side_effect=slow_candidates),
            patch.object(access, "_owned_world") as owned,
            patch("application_state.media.get_asset") as get_asset,
        ):
            asyncio.run(exercise())
        owned.assert_called_once_with("owner", "world")
        get_asset.assert_called_once_with(req.state.hosted_route_asset_id, access.hosted_world_media_owner("world"))

    def test_empty_candidates_still_deny(self):
        with (
            patch.object(access, "_hosted_subject", return_value="owner"),
            patch.object(access, "_owner_world_candidates", return_value=frozenset()),
        ):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(access.resolve_hosted_saved_artwork(request()))
        self.assertEqual(caught.exception.status_code, 403)

    def test_lookup_unavailable_remains_unavailable(self):
        with (
            patch.object(access, "_hosted_subject", return_value="owner"),
            patch.object(access, "_owner_world_candidates", side_effect=access._unavailable()),
        ):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(access.resolve_hosted_saved_artwork(request()))
        self.assertEqual(caught.exception.status_code, 503)

    def test_owner_revocation_after_asset_read_still_denies(self):
        req = request()
        with (
            patch.object(access, "_hosted_subject", return_value="owner"),
            patch.object(access, "_owner_world_candidates", return_value=frozenset({"world"})),
            patch.object(access, "_owned_world", side_effect=access._denied()),
            patch("application_state.media.get_asset"),
        ):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(access.resolve_hosted_saved_artwork(req))
        self.assertEqual(caught.exception.status_code, 403)
        self.assertFalse(hasattr(req.state, "hosted_saved_artwork"))

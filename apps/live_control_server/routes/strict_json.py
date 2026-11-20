"""One exact JSON parsing gate for native reviewed-write routes."""

import json
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class StrictJSONRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def strict(request: Request):
            try:
                json.loads(
                    await request.body(),
                    object_pairs_hook=_unique,
                    parse_constant=lambda _: (_ for _ in ()).throw(
                        ValueError("nonfinite JSON")
                    ),
                )
            except (ValueError, UnicodeDecodeError):
                raise HTTPException(
                    422, detail={"code": "invalid_json"}
                ) from None
            return await handler(request)

        return strict

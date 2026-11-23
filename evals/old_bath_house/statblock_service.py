"""Run the statblock service's ordinary routes against an isolated emulator."""

import argparse
import os
import re


def build(project):
    if not re.fullmatch(r"buddy-bath-fixture-[a-f0-9]{12}", project):
        raise ValueError("Expected a dedicated benchmark Firestore project")
    if not re.fullmatch(r"127\.0\.0\.1:[0-9]+", os.environ.get("FIRESTORE_EMULATOR_HOST", "")):
        raise ValueError("Expected a loopback Firestore emulator")
    if not os.environ.get("DUNGEONBUDDY_INTERNAL_API_KEY"):
        raise ValueError("Expected a disposable internal service key")
    os.environ.update({
        "GOOGLE_CLOUD_PROJECT": project,
        "STATBLOCKS_V1_FEATURE_ENABLED": "false",
        "STATBLOCKS_V1_ALLOW_READS_WHEN_DISABLED": "true",
        "STATBLOCKS_V1_ASSET_GATEWAY_ENABLED": "false",
    })

    from fastapi import FastAPI
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.firestore import Client
    from statblocks_v1.api import dependencies
    from statblocks_v1.api.health import health_router, liveness_router
    from statblocks_v1.api.http_errors import register_error_handlers
    from statblocks_v1.api.router import router
    from statblocks_v1.infrastructure.runtime import build_candidate_repository, build_persistence_repository

    client = Client(project=project, credentials=AnonymousCredentials())
    dependencies.configure_candidate_repository_factory(lambda: build_candidate_repository(client))
    dependencies.configure_persistence_repository_factory(lambda: build_persistence_repository(client))
    app = FastAPI()
    register_error_handlers(app)
    for routes in (router, health_router, liveness_router):
        app.include_router(routes)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(build(args.project), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()

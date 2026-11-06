"""Shared producer labels for Core-admitted sources; never source or fact authority."""

def source_display_metadata(items, world_id):
    """Producer display metadata only, after Core has authorized membership."""
    from application_state.source import service as sources
    from application_state.source.naming import registered_source_name
    from application_state.content import pages
    from application_state.errors import ApplicationStateError
    from psycopg import Error as DatabaseError

    recap_namespace = "dungeonbuddy.app-recap-source.v1"
    page_namespace = "dungeonbuddy.workspace-document-registry"
    recaps = [item for item in items if item.origin and item.origin.namespace == recap_namespace]
    page_items = [item for item in items if item.origin and item.origin.namespace == page_namespace]
    revisions, page_records = {}, {}
    if recaps:
        try:
            revisions = {
                (row.source_artifact_id, str(row.source_revision_id)): row
                for row in sources.get_source_revision_metadata(
                    bindings=[(item.origin.object_id, item.source_revision.content_sha256)
                              for item in recaps], world_id=world_id,
                )
            }
        except (ApplicationStateError, DatabaseError):
            pass  # Native source reads remain independent; label coverage is explicit below.
    if page_items:
        try:
            page_records = {
                str(state.page.work_object_id): state.page
                for state in pages.page_inventory(world_id=world_id, status=None)
            }
        except (ApplicationStateError, DatabaseError):
            pass
    navigation = []
    for item in items:
        classification = item.source_artifact.source_classification
        kind = {"dungeonbuddy.source:session_recap": "recap",
                "dungeonbuddy.source:worldbuilding": "worldbuilding"}.get(classification, "other")
        row = dict(label=None, kind=kind, campaign_id=None, session_id=None,
                   status="unavailable", metadata_revision=None,
                   origin_matches_current_metadata=None)
        origin = item.origin
        if origin and origin.namespace == recap_namespace:
            meta = revisions.get((origin.object_id, origin.revision_id))
            if (meta is not None and meta.world_id == world_id
                    and meta.content_sha256 == item.source_revision.content_sha256):
                row.update(label=registered_source_name(meta.model_dump(mode="json")),
                           campaign_id=meta.campaign_id, session_id=meta.session_id,
                           metadata_revision=str(meta.source_revision_id),
                           origin_matches_current_metadata=True)
        elif origin and origin.namespace == page_namespace:
            page = page_records.get(origin.object_id)
            if page is not None and page.world_id == world_id:
                revision = f"registry-revision:{page.object_revision}"
                row.update(label=page.title.strip() or None, campaign_id=page.campaign_id,
                           metadata_revision=revision,
                           origin_matches_current_metadata=origin.revision_id == revision)
        if row["label"]:
            row["status"] = "available"
        navigation.append(row)
    return navigation


def source_display_name(display, fallback):
    """One readable label format; it carries no source/fact authority."""
    if display is None or display['status'] != 'available':
        return fallback + ' (source name unavailable)'
    parts = [display['label']]
    if display['campaign_id']:
        parts.append('campaign: ' + display['campaign_id'])
    if display['session_id']:
        parts.append('session: ' + display['session_id'])
    if display['origin_matches_current_metadata'] is False:
        parts.append('current page label; selected source is an older revision')
    return ' · '.join(parts)


def opened_source_display_label(prepared, member):
    """Optional naming only, after the caller's fresh access/exact-byte check."""
    from dungeonmind.application.vnext import list_admitted_native_text_sources
    try:
        artifact, revision = member.artifact, member.revision
        items = [item for item in list_admitted_native_text_sources(prepared.access).sources
            if (item.source_artifact.source_artifact_id, item.source_revision.source_revision_id,
                item.source_revision.content_sha256)
            == (artifact.source_artifact_id, revision.source_revision_id, revision.content_sha256)]
        if len(items) != 1:
            return None
        display = source_display_metadata(items, prepared.authority.managed_world_id)[0]
        return source_display_name(display, 'Source') if display['status'] == 'available' else None
    except Exception:
        # Presentation lookup cannot revoke an already authorized exact read.
        # The caller performs all access and byte checks before entering here.
        return None

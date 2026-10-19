"""Play edition SQL. Caller owns transaction and Run-first lock ordering."""

from psycopg.rows import dict_row

_EDITION_COLUMNS = (
    "run_id",
    "world_id",
    "origin_artifact_id",
    "origin_revision_n",
    "origin_work_revision_id",
    "origin_content_sha256",
    "grammar_version",
    "structure_sha256",
    "head_revision",
    "created_at",
)
_REVISION_COLUMNS = (
    "run_id",
    "revision_n",
    "revision_id",
    "previous_revision",
    "markdown",
    "content_sha256",
    "committed_at",
    "command_id",
    "request_sha256",
    "expected_revision",
    "expected_sha256",
    "observed_run_revision",
    "expected_run_revision",
)


def get_edition(conn, run_id, *, lock=False):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM play.run_edition WHERE run_id = %s"
            + (" FOR UPDATE" if lock else ""),
            (run_id,),
        )
        return cur.fetchone()


def revisions(conn, run_id):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM play.run_edition_revision WHERE run_id = %s ORDER BY revision_n",
            (run_id,),
        )
        return cur.fetchall()


def insert_edition(conn, row):
    columns = _EDITION_COLUMNS
    conn.execute(
        f"INSERT INTO play.run_edition ({', '.join(columns)}) VALUES ({', '.join('%(' + c + ')s' for c in columns)})",
        row,
    )


def insert_revision(conn, row):
    columns = _REVISION_COLUMNS
    conn.execute(
        f"INSERT INTO play.run_edition_revision ({', '.join(columns)}) VALUES ({', '.join('%(' + c + ')s' for c in columns)})",
        row,
    )


def advance_head(conn, run_id, revision_n):
    conn.execute(
        "UPDATE play.run_edition SET head_revision = %s WHERE run_id = %s",
        (revision_n, run_id),
    )

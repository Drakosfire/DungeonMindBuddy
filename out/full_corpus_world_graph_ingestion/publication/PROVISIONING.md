# Full-corpus governed-publication authority provisioning

## Created 2026-09-14

Two local DungeonMind rehearsal databases were created for the sealed-candidate
publication experiment:

| Arm | Database | Network exposure | Initial graph heads / revisions |
| --- | --- | --- | --- |
| OpenAI GPT-5.4-mini | `dmb_full_corpus_openai` | Existing local server, loopback `127.0.0.1:54329` only | `0 / 0` |
| DeepSeek V4.1 Flash | `dmb_full_corpus_deepseek` | Existing local server, loopback `127.0.0.1:54329` only | `0 / 0` |

They were created with the DungeonMind schema copied from the existing local
Stage 4L authority using `pg_dump --schema-only --no-owner --no-privileges`.
No World, source, revision, identity, or campaign rows were copied. Therefore
the two authorities are equivalent and cannot contaminate one another.

No DSN, password, or other credential is stored in this repository or in the
publication artifacts.

## Current stop: no governed recap World genesis

The PR #715 code head (`7b4359bb063e22c0fb3f84c15d533b2420a5f757`) provides
the existing-World governed publication path, which requires a committed parent
World revision. The two databases intentionally have no parent revision.

This checkout does not contain a supported production service that initializes
a recap World from the canonical six-PC party registry. The historical
Eldyrwild bootstrap wrapper cannot run on this head because its owning service
is absent. Creating a World head with direct SQL would bypass source admission,
identity resolution, assertion qualification, and immutable revision creation;
it is prohibited for this experiment.

Consequently, no `World A` or `World B` has been claimed and no candidate has
been published. This is a systemic bootstrap capability gap, not a candidate or
model failure. The pre-created databases remain safe to retain until a governed
recap-genesis path is supplied; they contain schema only.

## Required continuation

Provide or land one model-independent governed initialization path which:

1. admits the canonical party-registry source;
2. creates exactly the six canonical PCs and required baseline vocabulary;
3. returns an immutable parent revision; and
4. can be run identically once per database.

Then run `tools/publish_full_corpus_world_graph.py` once per arm with that
database's isolated DSN and its initialized World ID. The runner verifies all
42 seals before it writes and records the revision chain in arm-specific
artifacts.

## Teardown / security closure

The databases are local-only and contain no campaign data or credentials. When
this experiment is complete or abandoned, an operator with access to the local
`dungeonmind-stage4j-rehearsal` container must terminate active connections and
drop exactly these two named databases:

```bash
docker exec dungeonmind-stage4j-rehearsal psql -U dungeonmind -d postgres \
  -c "DROP DATABASE dmb_full_corpus_openai WITH (FORCE)" \
  -c "DROP DATABASE dmb_full_corpus_deepseek WITH (FORCE)"
```

Do not drop the server, its volumes, or any database other than the two names
above. The command is intentionally not automated by the publication runner.

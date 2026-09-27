# Local managed-World storage

Selecting a World in Buddy does not switch database connections. One Buddy
deployment uses its configured DungeonMind and APP-STATE URLs for every managed
World. DungeonMind partitions graph heads by `world_id`; Buddy workspace
documents and Play Runs use that same value as their managed `campaign_id`.

The database pair is not the whole deployment. The Buddy runtime checkout also
owns the World-container/source registry and the corpus roots referenced by its
source records. Pointing a different checkout at the same two URLs does not
recreate those file-backed sources or the same list of available Worlds. Keep
the registry and source files with the deployment, and back them up together
with both databases before moving or restoring a local World.

The World selector uses the server's container list and verifies a URL selection
before any managed surface mounts. A missing graph head does not prevent source
or Plan authoring; graph reads and Ask must instead report unavailable. Legacy
Longmont C1/C2 still map to Eldyrwild and are not separate managed Worlds.

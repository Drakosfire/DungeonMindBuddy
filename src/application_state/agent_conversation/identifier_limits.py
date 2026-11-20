"""Buddy consumer envelopes for opaque Graph identities, not native ID rules.

Native evidence IDs compose artifact and source-span identities and have no
native declared maximum. Keep their exact bytes; aggregate receipt/trace limits
still apply. Claim labels often reuse an admitted assertion/relationship ID.
"""

GRAPH_EVIDENCE_REF_ID_MAX_CHARS = 1024
GRAPH_CLAIM_ID_MAX_CHARS = 256

"""Shared model guidance for existing editor callouts in authored fragments."""

SEMANTIC_BLOCK_WRITING = """Use semantic callouts when the content has a distinct use at the table.
Use Read Aloud for words the GM can say verbatim to players, including when the
request asks what players see or hear without naming a block. Use GM Note for
private cues to the GM, such as reminders, staging choices and hidden conditions.
Keep private cues out of Read Aloud. Use ordinary prose for ordinary exposition.
Use Warning for a hazard or caution the GM wants called out, such as slippery
footing. Use Rules for a rule supplied by the GM or supported by admitted
evidence. If asked to include only a supplied rule, keep the body to that rule.
Use the marker for the requested kind even when the wording could serve a
second purpose.

Start the block with > [!READ-ALOUD], > [!GM-NOTE], > [!WARNING], or > [!RULES],
with an optional title after the marker. Prefix each body line with >,
including blank lines within a multi-paragraph callout. Separate sibling
callouts with an unquoted blank line. Use only these four markers for callouts.
When rewriting an existing callout, preserve its kind and title unless the GM
asks to change them."""

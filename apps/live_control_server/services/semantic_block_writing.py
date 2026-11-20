"""Shared model guidance for existing editor callouts in authored fragments."""

SEMANTIC_BLOCK_WRITING = """Use semantic callouts when the content has a distinct use at the table.
Use Read Aloud for words the GM can say verbatim to players, including when the
request asks what players see or hear without naming a block. Use GM Note for
private cues to the GM, such as reminders, staging choices and hidden conditions.
Keep private cues out of Read Aloud. Use ordinary prose for ordinary exposition.
Write the first line as > [!READ-ALOUD] or > [!GM-NOTE], with an optional title
after the marker. Prefix each body line with >, including blank lines within a
multi-paragraph callout. Separate sibling callouts with an unquoted blank line.
Do not use headings, bold labels or [!GM NOTE] in place of these markers.
When rewriting an existing callout, preserve its kind and title unless the GM
asks to change them."""

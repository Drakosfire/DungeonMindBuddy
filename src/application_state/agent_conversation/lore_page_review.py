"""User text witness for an inert standalone lore-page review."""

from typing import Literal

from pydantic import Field

from .collaboration import Closed


class LorePageTitleWitness(Closed):
    instruction: str = Field(
        min_length=1,
        max_length=2000,
        description="Quote the exact author instruction requesting this page.",
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        pattern=r"^[^\n\r]+$",
        description="Quote the requested page title from that instruction.",
    )

    def bind(self, author_text: str) -> str:
        """Check the literal witness against the producing author turn."""
        if self.instruction != self.instruction.strip() or self.title != self.title.strip():
            raise ValueError("Lore page witness has surrounding whitespace")
        if not self.title or not self.instruction or author_text.count(self.instruction) != 1:
            raise ValueError("Lore page instruction must occur once in the author turn")
        before, found, after = self.instruction.partition(self.title)
        if not found or self.title in after:
            raise ValueError("Lore page title must occur once in the selected instruction")
        if (before and before[-1].isalnum()) or (after and after[0].isalnum()):
            raise ValueError("Lore page title must select whole words")
        return self.title


class ProposedLorePage(Closed):
    """Review an author-requested standalone page in conversation. Use no answer segments
    for a blank page. For a populated page, put its body in source passage claims and
    use invented-idea segments only for material explicitly presented as proposed."""
    kind: Literal["lore_page"]
    destination: LorePageTitleWitness

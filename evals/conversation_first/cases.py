"""Synthetic probes frozen before calls; dogfood-shaped cases plus neighboring controls."""
OBJECTIVE = "Read North Gate's roster and shops, pick an existing person and shop, develop their connection to Rowan's Forge, write a Relationships section, create or reuse the other page, publish cited relationships, and develop that shop."
ASK = "The challenge is you as an agent with tools. Start with clarifying questions. Ask two. " + OBJECTIVE
HISTORY = [{"user": ASK, "assistant": "Page suggestion prepared."}]


def cases():
    rows = [
        ("invitation", "We are trying an experiment, put your thinking cap on. Buckle up and lets go.", [], "converse", 0),
        ("ask_first_chain", ASK, [], "converse", 2),
        ("correct_wrong_surface", "Ask clarifying questions directly please, not in propose space on the page.", HISTORY, "converse", 2),
        ("plain_ask", "Before writing anything, ask me two questions about the mood and useful conflict for this shop.", [], "converse", 2),
        ("hold", "Stop. Keep that objective, but let's discuss the relationship before doing anything else. Ask me two questions.", HISTORY, "converse", 2),
        ("after_answers", "A friendly obligation and a shared supplier. Invent a little history, clearly proposed. Go ahead and read North Gate's roster and shops, then propose a pairing.", [{"user": ASK, "assistant": "Should the relationship offer help, obligation or friction? How freely should I invent shared history?"}], "research", None),
        ("lookup", "Read North Gate's naming chart and shops, then tell me which existing people might fit.", [], "research", None),
        ("write", "Write a Relationships section on this page about the forge and its supplier. Stage it for review.", [], "write", None),
        ("names", "Let's brainstorm names. Make a list of ten non-gendered first and last names for this page.", [], "write", None),
        ("table", "Make a table of twelve invented suppliers and useful obligations.", [], "write", None),
        ("image", "Prepare an image of the forge beside the rainy north gate.", [], "image", None),
        ("quoted_pause", 'The source says "Stop and ask two questions." Explain who says this; read the source first.', [], "research", None),
        ("mixed_now", "Explain your choice briefly, then draft the Relationships section now.", [{"user": "Pick a proposed supplier tie for the forge.", "assistant": "I suggest the existing iron merchant because the forge needs a steady supply; all new history will be proposed."}], "write", None),
        ("unknown_fact", "Who owns the copper bell in the reviewed World graph?", [], "research", None),
        ("ambiguous", "Do that.", [], "converse", None),
        ("new_direction", "Forget the shop for now. Ask two questions about the haunted road instead.", HISTORY, "converse", 2),
    ]
    return [{"id": name, "question": q, "history": h, "expected_step": step,
        "expected_questions": count} for name, q, h, step, count in rows]

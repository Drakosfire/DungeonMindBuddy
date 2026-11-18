"""Editable tabletop Markdown projected from reviewed mechanics."""

from collections import defaultdict

from apps.live_control_server.integrations.dungeonmind_statblocks.generated import StatblockDefinitionV1Input


_RULE_SECTIONS = {
    "trait": "Traits",
    "action": "Actions",
    "bonus_action": "Bonus actions",
    "reaction": "Reactions",
    "legendary_action": "Legendary actions",
    "lair_action": "Lair actions",
}


def _label(value):
    return value.replace("_", " ").capitalize()


def _values(value):
    """Render optional structured qualifications as human-readable detail."""
    if isinstance(value, dict):
        if set(value) == {"unit", "value"}:
            return f"{value['value']} {value['unit']}"
        return "; ".join(
            f"{_label(key)}: {text}"
            for key, item in value.items()
            if (text := _values(item))
        )
    if isinstance(value, list):
        return ", ".join(text for item in value if (text := _values(item)))
    if value is None:
        return ""
    return ("yes" if value else "no") if isinstance(value, bool) else str(value)


def render_variant_markdown(definition: StatblockDefinitionV1Input) -> str:
    data = definition.model_dump(mode="json")
    identity = data["identity"]
    description = ", ".join(filter(None, (
        " ".join(filter(None, (identity["size"], identity["creature_type"]))),
        _values(identity["subtypes"]),
        identity["alignment"],
    )))
    lines = [f"# {identity['name']}", "", f"*{description}*", ""]
    hit_points = data["vitality"]["hit_points"]
    if hit_points and hit_points["formula"]:
        formula = hit_points["formula"]
        dice = f"{formula['count']}d{formula['die']}"
        if formula["modifier"]:
            dice += f"{formula['modifier']:+d}"
        average = hit_points["displayed_average"]
        lines.append(f"**Hit points** {average} ({dice})" if average is not None else f"**Hit points** {dice}")
    elif hit_points:
        value = hit_points["fixed_value"]
        if value is not None:
            lines.append(f"**Hit points** {value}")

    for armor in data["defenses"]["armor_classes"]:
        condition = f" ({armor['condition']})" if armor["condition"] else ""
        label = armor["label"] or "Armor class"
        standing = "default" if armor["default"] else "alternate"
        lines.append(f"**{label}** {armor['value']} ({standing}){condition}")
    for key, title in (
        ("movement", "Movement"), ("senses", "Senses"),
        ("communication", "Communication"), ("proficiencies", "Proficiencies"),
        ("challenge", "Challenge"), ("lair", "Lair"), ("resources", "Resources"),
        ("phases", "Phases"), ("flavor_text", "Description"), ("ruleset", "Ruleset"),
    ):
        details = _values(data[key])
        if details:
            lines.append(f"**{title}** {details}")
    for key in ("damage_interactions", "condition_immunities"):
        if (details := _values(data["defenses"][key])):
            lines.append(f"**{_label(key)}** {details}")

    lines.extend(["", "| STR | DEX | CON | INT | WIS | CHA |", "| --- | --- | --- | --- | --- | --- |"])
    scores = [data["abilities"][key] for key in (
        "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
    )]
    lines.append("| " + " | ".join(
        str(score) if score is not None else "—" for score in scores
    ) + " |")

    sections = defaultdict(list)
    for rule in data["rule_elements"]:
        sections[rule["section"]].append(rule)
    for section, rules in sections.items():
        lines.extend(["", f"## {_RULE_SECTIONS.get(section, _label(section))}"])
        for rule in rules:
            lines.extend(["", f"**{rule['name']}.** {rule['rules_text']}", f"- **Rule reference** `{rule['key']}`"])
            activation = rule["activation"]
            usage = rule["usage"]
            mechanic = rule["mechanic"]
            for label, value in (
                ("Timing", activation["timing_text"]),
                ("Trigger", activation["trigger"]),
                ("Use", usage if usage["kind"] != "manual" or usage["resource_key"] else usage["refresh_text"]),
                ("Cost", rule["costs"]),
                ("Mechanics", mechanic if mechanic["kind"] != "human_adjudicated" else None),
            ):
                if (text := _values(value)):
                    lines.append(f"- **{label}** {text}")
    return "\n".join(lines)

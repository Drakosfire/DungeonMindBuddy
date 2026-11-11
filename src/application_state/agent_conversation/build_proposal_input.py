"""Decode the sole Build proposal input carrier shared by the writer proofs."""

from .source_writer_output import strict_json


def proposal_packet_text(body):
    value = body.get("input")
    if isinstance(value, str):
        return value
    if not isinstance(value, list) or len(value) != 1:
        return None
    message = value[0]
    if (not isinstance(message, dict) or set(message) != {"role", "content"}
            or message["role"] != "user" or not isinstance(message["content"], list)
            or len(message["content"]) != 2):
        return None
    text, image = message["content"]
    if (not isinstance(text, dict) or set(text) != {"type", "text"}
            or text["type"] != "input_text" or not isinstance(text["text"], str)
            or not isinstance(image, dict) or set(image) != {"type", "image_url", "detail"}
            or image["type"] != "input_image" or image["detail"] != "high"
            or not isinstance(image["image_url"], str)
            or not image["image_url"].startswith("data:image/jpeg;base64,")):
        return None
    packet = strict_json(text["text"])
    if not isinstance(packet, dict) or packet.get("task") != "compose_current_page":
        return None
    return text["text"]

import json
from urllib import parse


def decode_payload(payload: str) -> dict:
    raw_payload = payload.split("request=", 1)[1]
    decoded = parse.unquote(raw_payload)
    parsed_top = json.loads(decoded)
    first_request = parsed_top["requests"][0]
    body_str = first_request["body"]
    body_dict = json.loads(body_str)
    first_request["body"] = body_dict
    return parsed_top


def encode_payload(payload: dict) -> str:
    for req in payload.get("requests", []):
        body_value = req.get("body")
        if isinstance(body_value, dict):
            req["body"] = json.dumps(body_value)

    top_level_json = json.dumps(payload)
    url_encoded = parse.quote(top_level_json)

    return f"request={url_encoded}"

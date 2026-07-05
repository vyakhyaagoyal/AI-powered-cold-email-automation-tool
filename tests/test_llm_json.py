import pytest

from core.llm import _parse_json_response


def test_parse_json_response_accepts_fenced_json():
    raw = '''```json
{
  "subject": "A stronger subject line",
  "body": "Hello there"
}
```'''

    assert _parse_json_response(raw) == {
        "subject": "A stronger subject line",
        "body": "Hello there",
    }


def test_parse_json_response_rejects_non_object_json():
    with pytest.raises(Exception):
        _parse_json_response('{"subject": "x"}')

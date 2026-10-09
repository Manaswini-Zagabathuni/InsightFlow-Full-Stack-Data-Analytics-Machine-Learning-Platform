import json
import logging

from app.core.logging import JsonFormatter


def test_json_logging_escapes_messages_and_includes_context():
    record = logging.LogRecord(
        name="insightflow.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='request returned "201 Created"',
        args=(),
        exc_info=None,
    )
    record.dataset_id = "dataset-1"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == 'request returned "201 Created"'
    assert payload["dataset_id"] == "dataset-1"
    assert payload["level"] == "INFO"

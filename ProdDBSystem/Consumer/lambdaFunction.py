"""AWS Lambda handler for processing SQS events.

Receives batched SQS records, extracts the event type and data from each
message body, and dispatches to the appropriate handler in Event.py.
"""

import json
import logging
from Event import submitPracticeQuiz, purchaseCourse, updateModule, completeModule, deleteAccount

logging.basicConfig(level=logging.INFO, format="%(filename)s - %(levelname)s - %(message)s")

EVENT_HANDLERS = {
    "submitPracticeQuiz": submitPracticeQuiz,
    "purchaseCourse": purchaseCourse,
    "updateModule": updateModule,
    "completeModule": completeModule,
    "deleteAccount": deleteAccount,
}


def handler(event, context):
    """Process a batch of SQS records and dispatch each to its event handler.

    Iterates over all records in the SQS event, parses the message body,
    and calls the matching handler function based on the eventType field.

    Args:
        event: The Lambda event dict containing a list of SQS Records.
        context: The Lambda context object (unused).

    Returns:
        A dict with statusCode 200 and a success message body.
    """
    logging.info("Received event: %s", json.dumps(event))

    for record in event["Records"]:
        message = json.loads(record["body"])
        eventType = message.get("eventType")
        data = message.get("data")

        if data is None:
            logging.warning("No data found in message: %s", json.dumps(message))
            continue

        handlerFn = EVENT_HANDLERS.get(eventType)
        if handlerFn is None:
            logging.warning("Unknown event type: %s", eventType)
            continue

        handlerFn(data)
        logging.info("Processed event type: %s", eventType)

    return {
        "statusCode": 200,
        "body": json.dumps("Event processed successfully!")
    }

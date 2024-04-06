import json
import base64
from near_lake_framework import near_primitives

def handle_streamer_message(streamer_message: near_primitives.StreamerMessage):
    block_timestamp = streamer_message.block.header.timestamp

    for shard in streamer_message.shards:
        # 1. HANDLE LOGS
        for receipt_execution_outcome in shard.receipt_execution_outcomes:
            for log_index, log in enumerate(
                receipt_execution_outcome.execution_outcome.outcome.logs, start=1
            ):
                if not log.startswith("EVENT_JSON:"):
                    continue
                try:
                    parsed_log = json.loads(log[len("EVENT_JSON:") :])
                except json.JSONDecodeError:
                    print(
                        f"Receipt ID: `{receipt_execution_outcome.receipt.receipt_id}`\nError during parsing logs from JSON string to dict"
                    )
                    continue

                log_data = parsed_log.get("data")
                receipt = receipt_execution_outcome.receipt

        # 2. HANDLE METHOD CALLS
        # Skip if the tx failed
        if (
            "SuccessReceiptId"
            not in receipt_execution_outcome.execution_outcome.outcome.status
            and "SuccessValue"
            not in receipt_execution_outcome.execution_outcome.outcome.status
        ):
            # consider logging failures to logging service; for now, just skip
            continue

        for index, action in enumerate(
            receipt_execution_outcome.receipt.receipt["Action"]["actions"]
        ):
            try:
                method_name = action["FunctionCall"]["method_name"]
                args = json.loads(base64.b64decode(action["FunctionCall"]["args"]))
                deposit = action["FunctionCall"]["deposit"]
                gas = action["FunctionCall"]["gas"]
                receipt = receipt_execution_outcome.receipt
            except Exception as e:  # pylint: disable=bare-except
                print(
                    f"Error during parsing method call from JSON string to dict\n{e}"
                )
                pass


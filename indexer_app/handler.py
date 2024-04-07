import base64
import json

from near_lake_framework import near_primitives


def handle_streamer_message(streamer_message: near_primitives.StreamerMessage):
    block_timestamp = streamer_message.block.header.timestamp
    block_height = streamer_message.block.header.height
    print(f"Block Height: {block_height}, Block Timestamp: {block_timestamp}")

    for shard in streamer_message.shards:
        for receipt_execution_outcome in shard.receipt_execution_outcomes:
            # 1. HANDLE LOGS
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
                if "FunctionCall" not in action:
                    continue
                receipt = receipt_execution_outcome.receipt
                try:
                    function_call = action["FunctionCall"]
                    method_name = function_call["method_name"]
                    args = function_call["args"]
                    deposit = function_call["deposit"]
                    gas = function_call["gas"]
                    decoded_bytes = base64.b64decode(args) if args else b"{}"
                    # Assuming the decoded data is UTF-8 text
                    try:
                        decoded_text = decoded_bytes.decode("utf-8")
                        args_dict = json.loads(decoded_text)
                    except UnicodeDecodeError:
                        # Handle case where the byte sequence cannot be decoded to UTF-8
                        print(f"Cannot decode args to UTF-8 text: {decoded_bytes}")
                        args_dict = {}
                    except json.JSONDecodeError:
                        # Handle case where the text cannot be parsed as JSON
                        print(f"Decoded text is not valid JSON: {decoded_text}")
                        args_dict = {}

                except Exception as e:
                    print(
                        f"Error during parsing method call from JSON string to dict\n{e}"
                    )

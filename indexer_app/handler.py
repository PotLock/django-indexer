import base64
import json
from datetime import datetime

from django.core.cache import cache
from near_lake_framework import near_primitives

from .logging import logger
from .utils import (
    handle_default_list_status_change,
    handle_list_admin_removal,
    handle_list_registration_update,
    handle_list_upvote,
    handle_new_donations,
    handle_new_list,
    handle_new_list_registration,
    handle_new_pot,
    handle_new_pot_factory,
    handle_payout_challenge,
    handle_pot_application,
    handle_pot_application_status_change,
    handle_set_payouts,
    handle_transfer_payout,
)
from pots.utils import match_pot_factory_version_pattern


async def handle_streamer_message(streamer_message: near_primitives.StreamerMessage):
    block_timestamp = streamer_message.block.header.timestamp
    block_height = streamer_message.block.header.height
    await cache.aset(
        "block_height", block_height
    )  # TODO: add custom timeout if it should be valid for longer than default (5 minutes)
    logger.info(f"Block Height: {block_height}, Block Timestamp: {block_timestamp}")
    # if block_height == 111867204:
    #     with open("indexer_outcome2.json", "w") as file:
    #         file.write(f"{streamer_message}")

    for shard in streamer_message.shards:
        for receipt_execution_outcome in shard.receipt_execution_outcomes:
            # we only want to proceed if it's a potlock tx and it succeeded.... (unreadable if statement?)
            if not receipt_execution_outcome.receipt.receiver_id.endswith(
                "potlock.near"
            ) or (
                "SuccessReceiptId"
                not in receipt_execution_outcome.execution_outcome.outcome.status
                and "SuccessValue"
                not in receipt_execution_outcome.execution_outcome.outcome.status
            ):
                continue
            # 1. HANDLE LOGS

            log_data = []

            for log_index, log in enumerate(
                receipt_execution_outcome.execution_outcome.outcome.logs, start=1
            ):
                if not log.startswith("EVENT_JSON:"):
                    continue
                try:
                    parsed_log = json.loads(log[len("EVENT_JSON:") :])
                except json.JSONDecodeError:
                    logging.warning(
                        f"Receipt ID: `{receipt_execution_outcome.receipt.receipt_id}`\nError during parsing logs from JSON string to dict"
                    )
                    continue

                log_data.append(parsed_log.get("data")[0])

                # TODO: handle set_source_metadata logs for various contracts

            # 2. HANDLE METHOD CALLS
            # Skip if the tx failed
            # if (
            #     "SuccessReceiptId"
            #     not in receipt_execution_outcome.execution_outcome.outcome.status
            #     and "SuccessValue"
            #     not in receipt_execution_outcome.execution_outcome.outcome.status
            # ):
            #     # consider logging failures to logging service; for now, just skip
            #     print("here we are...")
            #     continue

            for index, action in enumerate(
                receipt_execution_outcome.receipt.receipt["Action"]["actions"]
            ):
                if "FunctionCall" not in action:
                    continue
                receipt = receipt_execution_outcome.receipt
                status_obj = receipt_execution_outcome.execution_outcome.outcome
                created_at = datetime.fromtimestamp(block_timestamp / 1000000000)

                try:
                    function_call = action["FunctionCall"]
                    method_name = function_call["method_name"]
                    args = function_call["args"]
                    decoded_bytes = base64.b64decode(args) if args else b"{}"
                    signer_id = receipt.receipt["Action"]["signer_id"]
                    receiver_id = receipt.receiver_id
                    predecessor_id = receipt.predecessor_id
                    # Assuming the decoded data is UTF-8 text
                    try:
                        decoded_text = decoded_bytes.decode("utf-8")
                        args_dict = json.loads(decoded_text)
                    except UnicodeDecodeError:
                        # Handle case where the byte sequence cannot be decoded to UTF-8
                        logger.warning(f"Cannot decode args to UTF-8 text: {decoded_bytes}")
                        args_dict = {}
                    except json.JSONDecodeError:
                        # Handle case where the text cannot be parsed as JSON
                        logger.warning(f"Decoded text is not valid JSON: {decoded_text}")
                        args_dict = {}

                    match method_name:
                        case "new":
                            if match_pot_factory_version_pattern(receipt.receiver_id):
                                logger.info(f"matched for factory pattern: {args_dict}")
                                await handle_new_pot_factory(
                                    args_dict, receiver_id, created_at
                                )
                            else:
                                logger.info(f"new pot deployment: {args_dict}, {action}")
                                await handle_new_pot(
                                    args_dict,
                                    receiver_id,
                                    signer_id,
                                    predecessor_id,
                                    receipt.receipt_id,
                                    created_at,
                                )
                            break

                        case "assert_can_apply_callback":
                            logger.info(f"application case: {args_dict}, {action}, {receipt}")
                            await handle_pot_application(
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt,
                                status_obj,
                                created_at,
                            )
                            break

                        case "apply":
                            logger.info(f"application case 2: {args_dict}, {action}, {receipt}")
                            await handle_pot_application(
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt,
                                status_obj,
                                created_at,
                            )
                            break

                        case "donate":  # TODO: donate that produces result
                            logger.info(f"switching bazooka to knifee works!! donate his blood: {args_dict}, {receipt}, {action}, {log_data}")
                            await handle_new_donations(
                                args_dict,
                                receiver_id,
                                signer_id,
                                "direct",
                                receipt,
                                status_obj,
                                log_data,
                                created_at,
                            )
                            break

                        case "handle_protocol_fee_callback":
                            logger.info(f"donations to pool incoming: {args_dict}, {receipt}, {receipt_execution_outcome}")
                            await handle_new_donations(
                                args_dict,
                                receiver_id,
                                signer_id,
                                "pot",
                                receipt,
                                status_obj,
                                log_data,
                                created_at,
                            )
                            break

                        case "transfer_funds_callback":
                            logger.info(f"new version donations to pool incoming: {args_dict}, {action}")
                            await handle_new_donations(
                                args_dict,
                                receiver_id,
                                signer_id,
                                "direct",
                                receipt,
                                status_obj,
                                log_data,
                                created_at,
                            )
                            break

                        case (
                            "register_batch"
                        ):  # TODO: listen for create_registration event instead of method call
                            logger.info(f"registrations incoming: {args_dict}, {action}")
                            if receiver_id != "lists.potlock.near":
                                break
                            await handle_new_list_registration(
                                args_dict, receiver_id, signer_id, receipt, status_obj
                            )
                            break

                        case "chef_set_application_status":
                            logger.info(f"application status change incoming: {args_dict}")
                            await handle_pot_application_status_change(
                                args_dict, receiver_id, signer_id, receipt, status_obj
                            )
                            break

                        case "admin_set_default_project_status":
                            logger.info(
                                f"registry default status setting incoming: {args_dict}"
                            )
                            await handle_default_list_status_change(
                                args_dict, receiver_id, status_obj
                            )
                            break

                        case (
                            "update_registration"
                        ):  # TODO: listen for update_registration event instead of method call
                            logger.info(
                                f"project registration status update incoming: {args_dict}",
                            )
                            await handle_list_registration_update(
                                args_dict, receiver_id, status_obj
                            )
                            break
                        # TODO: handle delete_registration event
                        case "chef_set_payouts":
                            logger.info(f"setting payout....: {args_dict}")
                            await handle_set_payouts(args_dict, receiver_id, receipt)
                            break

                        case "challenge_payouts":
                            logger.info(f"challenge payout: {args_dict}")
                            await handle_payout_challenge(
                                args_dict, receiver_id, signer_id, receipt.receipt_id
                            )
                            break

                        case "transfer_payout_callback":
                            logger.info(f"fulfilling payouts..... {args_dict}")
                            await handle_transfer_payout(
                                args_dict, receiver_id, receipt.receipt_id, created_at
                            )
                            break

                        case (
                            "owner_remove_admins"
                        ):  # TODO: use update_admins event instead of method call to handle all cases
                            logger.info(f"attempting to remove admins....: {args_dict}")
                            if receiver_id != "lists.potlock.near":
                                break
                            await handle_list_admin_removal(
                                args_dict, receiver_id, signer_id, receipt.receipt_id
                            )
                            break

                        case "create_list":
                            logger.info(f"creating list... {args_dict}, {action}")
                            if receiver_id != "lists.potlock.near":
                                break
                            await handle_new_list(signer_id, receiver_id, status_obj)
                            break

                        case "upvote":
                            logger.info(f"up voting... {args_dict}")
                            if receiver_id != "lists.potlock.near":
                                break
                            await handle_list_upvote(
                                args_dict, receiver_id, signer_id, receipt.receipt_id
                            )
                            break
                        # TODO: handle remove upvote

                except Exception as e:
                    logger.warning(
                        f"Error during parsing method call from JSON string to dict\n{e}"
                    )
                    # with open("indexer_error.txt", "a") as file:
                    #     file.write(f"{e}\n")

import asyncio
import base64
import json
import time
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from near_lake_framework import near_primitives
from stellar_sdk.soroban_rpc import GetEventsResponse


from base.utils import convert_ns_to_utc
from grantpicks.models import StellarEvent
from nadabot.utils import match_nadabot_registry_pattern
from pots.utils import is_relevant_account, match_pot_factory_pattern, match_pot_subaccount_pattern

from .logging import log_memory_usage, logger
from .utils import (
    handle_add_nadabot_admin,  # handle_batch_donations,
    handle_add_stamp,
    handle_default_list_status_change,
    handle_delete_list,
    handle_list_admin_ops,
    handle_list_owner_change,
    handle_list_registration_removal,
    handle_list_registration_update,
    handle_list_update,
    handle_list_upvote,
    handle_new_donation,
    handle_new_group,
    handle_new_list,
    handle_new_list_and_reg,
    handle_new_list_registration,
    handle_new_nadabot_registry,
    handle_new_pot,
    handle_new_pot_factory,
    handle_new_provider,
    handle_payout_challenge,
    handle_payout_challenge_response,
    handle_pot_application,
    handle_pot_application_status_change,
    handle_pot_config_update,
    handle_registry_blacklist_action,
    handle_registry_unblacklist_action,
    handle_remove_upvote,
    handle_set_factory_configs,
    handle_set_payouts,
    handle_social_profile_update,
    handle_transfer_payout,
    handle_update_default_human_threshold,
)


async def handle_streamer_message(streamer_message: near_primitives.StreamerMessage):
    start_time = time.time()
    log_memory_usage("Start of handle_streamer_message")

    block_timestamp = streamer_message.block.header.timestamp
    block_height = streamer_message.block.header.height
    now_datetime = datetime.fromtimestamp(block_timestamp / 1000000000)
    # # Fire and forget the cache update
    # asyncio.create_task(cache.aset("block_height", block_height))
    # await cache.aset(
    #     "block_height", block_height
    # )  # TODO: add custom timeout if it should be valid for longer than default (5 minutes)
    formatted_date = convert_ns_to_utc(block_timestamp)
    logger.info(
        f"Block Height: {block_height}, Block Timestamp: {block_timestamp} ({formatted_date})"
    )
    # logger.info(
    #     f"Time after processing block info: {time.time() - start_time:.4f} seconds"
    # )
    # log_memory_usage("After processing block info")
    # if block_height == 111867204:
    #     with open("indexer_outcome2.json", "w") as file:
    #         file.write(f"{streamer_message}")

    for shard_index, shard in enumerate(streamer_message.shards):
        shard_start_time = time.time()
        for outcome_index, receipt_execution_outcome in enumerate(
            shard.receipt_execution_outcomes
        ):
            # we only want to proceed if the tx succeeded
            if (
                "SuccessReceiptId"
                not in receipt_execution_outcome.execution_outcome.outcome.status
                and "SuccessValue"
                not in receipt_execution_outcome.execution_outcome.outcome.status
            ):
                continue
            receiver_id = receipt_execution_outcome.receipt.receiver_id
            if (
                receiver_id != settings.NEAR_SOCIAL_CONTRACT_ADDRESS
                and not is_relevant_account(receiver_id)
            ):
                continue
            # 1. HANDLE LOGS
            log_data = []
            receipt = receipt_execution_outcome.receipt
            signer_id = receipt.receipt["Action"]["signer_id"]
            LISTS_CONTRACT = "lists." + settings.POTLOCK_TLA

            log_processing_start = time.time()
            for log_index, log in enumerate(
                receipt_execution_outcome.execution_outcome.outcome.logs, start=1
            ):
                if not log.startswith("EVENT_JSON:"):
                    continue
                try:
                    parsed_log = json.loads(log[len("EVENT_JSON:") :])
                    event_name = parsed_log.get("event")
                    print("parsa parsa...", parsed_log)
                    if event_name == "update_pot_config":
                        await handle_pot_config_update(
                            parsed_log.get("data")[0], receiver_id
                        )

                    if event_name == "add_or_update_provider":
                        await handle_new_provider(
                            parsed_log.get("data")[0], receiver_id, signer_id
                        )
                    elif event_name == "add_stamp":
                        await handle_add_stamp(
                            parsed_log.get("data")[0], receiver_id, signer_id
                        )
                    elif event_name == "update_default_human_threshold":
                        await handle_update_default_human_threshold(
                            parsed_log.get("data")[0], receiver_id
                        )
                    if event_name == "add_or_update_group":
                        await handle_new_group(parsed_log.get("data")[0], now_datetime)
                    if event_name == "blacklist_account":
                        await handle_registry_blacklist_action(
                            parsed_log.get("data")[0], receiver_id, now_datetime
                        )
                    if event_name == "unblacklist_account":
                        await handle_registry_unblacklist_action(
                            parsed_log.get("data")[0], receiver_id, now_datetime
                        )
                    if event_name == "delete_list":
                        await handle_delete_list(
                            parsed_log.get("data")[0]
                        )
                    if event_name == "owner_transfer":
                        if receiver_id != LISTS_CONTRACT:
                            continue
                        await handle_list_owner_change(
                            parsed_log.get("data")[0]
                        )
                    if event_name == "update_admins":
                        if receiver_id != LISTS_CONTRACT:
                            continue
                        await handle_list_admin_ops(
                            parsed_log.get("data")[0], receiver_id, signer_id, receipt.receipt_id
                        )
                    if event_name == "update_lis":
                        if receiver_id != LISTS_CONTRACT:
                            continue
                        await handle_list_update(
                            parsed_log.get("data")[0], receiver_id, signer_id, receipt.receipt_id
                        )
                except json.JSONDecodeError:
                    logger.warning(
                        f"Receipt ID: `{receipt_execution_outcome.receipt.receipt_id}`\nError during parsing logs from JSON string to dict"
                    )
                    continue

                log_data.append(parsed_log.get("data")[0])

                # TODO: handle set_source_metadata logs for various contracts

            # logger.info(
            #     f"Time to process logs for receipt {receipt_execution_outcome.receipt.receipt_id}: {time.time() - log_processing_start:.4f} seconds"
            # )
            # log_memory_usage("After processing logs")

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
            # method_call_processing_start = time.time()
            DONATE_CONTRACT = "donate." + settings.POTLOCK_TLA

            for index, action in enumerate(
                receipt_execution_outcome.receipt.receipt["Action"]["actions"]
            ):
                if "FunctionCall" not in action:
                    continue
                # receipt = receipt_execution_outcome.receipt
                status_obj = receipt_execution_outcome.execution_outcome.outcome

                try:
                    function_call = action["FunctionCall"]
                    method_name = function_call["method_name"]
                    args = function_call["args"]
                    decoded_bytes = base64.b64decode(args) if args else b"{}"
                    # signer_id = receipt.receipt["Action"]["signer_id"]
                    # receiver_id = receiver_id
                    predecessor_id = receipt.predecessor_id
                    result = status_obj.status.get("SuccessValue")
                    # Assuming the decoded data is UTF-8 text
                    try:
                        decoded_text = decoded_bytes.decode("utf-8")
                        args_dict = json.loads(decoded_text)
                    except UnicodeDecodeError:
                        # Handle case where the byte sequence cannot be decoded to UTF-8
                        logger.warning(
                            f"Cannot decode args to UTF-8 text: {decoded_bytes}"
                        )
                        args_dict = {}
                    except json.JSONDecodeError:
                        # Handle case where the text cannot be parsed as JSON
                        logger.warning(
                            f"Decoded text is not valid JSON: {decoded_text}"
                        )
                        args_dict = {}

                    match method_name:
                        case "set":  # handle near social profile data updates
                            if receiver_id == settings.NEAR_SOCIAL_CONTRACT_ADDRESS:
                                logger.info(f"setting profile data: {args_dict}")
                                await handle_social_profile_update(
                                    args_dict, receiver_id, signer_id
                                )
                        case "new":
                            if match_pot_factory_pattern(receiver_id):
                                logger.info(f"matched for factory pattern: {args_dict}")
                                await handle_new_pot_factory(
                                    args_dict, receiver_id, now_datetime
                                )
                            elif match_nadabot_registry_pattern(
                                receiver_id
                            ):  # matches registries in the pattern, version(v1).env(staging).nadabot.near
                                await handle_new_nadabot_registry(
                                    args_dict, receiver_id, now_datetime
                                )
                            elif match_pot_subaccount_pattern(receiver_id):
                                logger.info(
                                    f"new pot deployment: {args_dict}, {action}"
                                )
                                await handle_new_pot(
                                    args_dict,
                                    receiver_id,
                                    signer_id,
                                    predecessor_id,
                                    receipt.receipt_id,
                                    now_datetime,
                                )
                            break
                        # TODO: update to use handle_apply method??
                        case "assert_can_apply_callback":
                            logger.info(
                                f"application case: {args_dict}, {action}, {receipt}"
                            )
                            await handle_pot_application(
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt,
                                status_obj,
                                now_datetime,
                            )
                            break

                        case "apply":
                            logger.info(
                                f"application case 2: {args_dict}, {action}, {receipt}"
                            )
                            await handle_pot_application(
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt,
                                status_obj,
                                now_datetime,
                            )
                            break

                        ### Donation cases
                        ## SCENARIOS:
                        # 1. Pot donations
                        # tl;dr: only handle method calls that have a result, aka the final call in the chain. This could be "donate", "handle_protocol_fee_callback", or "sybil_callback".
                        # - handle_protocol_fee_callback (NOT called if protocol fee is bypassed)
                        #    - check result (will ALWAYS return DonationExternal)
                        # - sybil_callback (NOT called if there are no sybil requirements for the Pot)
                        #    - check result (MAY return DonationExternal)
                        #    - if result is not None, handle donation.
                        # - donate
                        #    - check result (will either return `DonationExternal`, if no CC calls, or `None` if CC calls were involved)
                        #    - if result is not None, handle donation. Otherwise ignore & listen for either handle_protocol_fee_callback or sybil_callback
                        #    - Example with result: https://nearblocks.io/txns/9beSPiZzR9Yu1951gC6AfQVCXiGPnBRxRFQsyfxUQr3H?tab=execution
                        #    - Example with no result: https://nearblocks.io/txns/7p9m3D2Ao3TX9BXXCKTFbBk51F2iEuSCi8r5gSesdkZ2?tab=execution
                        # 2. Direct donations
                        # - donate
                        #    - if result is not None, handle donation.
                        # - transfer_funds_callback
                        #    - check result (will always return DonationExternal IF it is a DonationTransfer)
                        #    - if result is not None, handle donation
                        #    - NB: this method was not implemented until early 2024; for older donations, use donate method
                        case (
                            "donate"
                            | "handle_protocol_fee_callback"
                            | "sybil_callback"
                            | "transfer_funds_callback"
                        ):
                            donation_type = (
                                "direct" if receiver_id == DONATE_CONTRACT else "pot"
                            )
                            logger.info(
                                f"New {donation_type} donation ({method_name}) --- ARGS: {args_dict}, RECEIPT: {receipt}, STATUS: {status_obj}, OUTCOME: {receipt_execution_outcome}, LOGS: {log_data}"
                            )
                            if not result:
                                logger.info("No result found. Skipping...")
                                break
                            decoded_success_val = base64.b64decode(result).decode(
                                "utf-8"
                            )
                            logger.info(f"Decoded success value: {decoded_success_val}")
                            if (
                                decoded_success_val == "null"
                            ):  # edge case that sometimes occurs where the response is a literal string "null", appears to be due to transfer_funds_callback returning None e.g. in the case of a ProtocolFeeCallback (see https://pikespeak.ai/transaction-viewer/78M3HCiBCeCu7jEk6KiVSJGr4utnV2aze8S5ZdEu16t8/detailed for example)
                                logger.info("Result is null. Skipping...")
                                break
                            try:
                                donation_data = json.loads(decoded_success_val)
                            except json.JSONDecodeError:
                                logger.error(
                                    f"Error decoding result to JSON: {decoded_success_val}"
                                )
                                donation_data = {}
                            await handle_new_donation(
                                args_dict,
                                receiver_id,
                                signer_id,
                                donation_type,
                                receipt,
                                donation_data,
                            )
                            break

                        case (
                            "register_batch"
                        ):  # TODO: listen for create_registration event instead of method call
                            logger.info(
                                f"registrations incoming: {args_dict}, {action}"
                            )
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_new_list_registration(
                                args_dict, receiver_id, signer_id, receipt, status_obj
                            )
                            break

                        case (
                            "unregister"
                        ):  # TODO: listen for create_registration event instead of method call
                            logger.info(
                                f"registrations revoke incoming: {args_dict}, {action}"
                            )
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_list_registration_removal(
                                args_dict, receiver_id
                            )
                            break

                        case "chef_set_application_status":
                            logger.info(
                                f"application status change incoming: {args_dict}"
                            )
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
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt.receipt_id,
                                now_datetime,
                            )
                            break

                        case "admin_update_payouts_challenge":
                            logger.info(f"challenge payout: {args_dict}")
                            await handle_payout_challenge_response(
                                args_dict,
                                receiver_id,
                                signer_id,
                                receipt.receipt_id,
                                now_datetime,
                            )
                            break

                        case "transfer_payout_callback":
                            logger.info(f"fulfilling payouts..... {args_dict}")
                            await handle_transfer_payout(
                                args_dict, receiver_id, receipt.receipt_id, now_datetime
                            )
                            break

                        case "create_list":
                            logger.info(f"creating list... {args_dict}, {action}")
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_new_list(signer_id, receiver_id, status_obj, None)
                            break

                        case "update_list":
                            logger.info(f"updating list... {args_dict}, {action}")
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_list_update(signer_id, receiver_id, status_obj, None)
                            break

                        case "upvote":
                            logger.info(f"up voting... {args_dict}")
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_list_upvote(
                                args_dict, receiver_id, signer_id, receipt.receipt_id, now_datetime
                            )
                            break
                        case "remove_upvote":
                            logger.info(f"removing upvote... {args_dict}")
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_remove_upvote(
                                args_dict, receiver_id, signer_id
                            )
                            break
                        case "owner_add_admins":
                            logger.info(f"adding admins.. {args_dict}")
                            if not match_nadabot_registry_pattern(receiver_id):
                                break
                            await handle_add_nadabot_admin(args_dict, receiver_id)
                            break
                        case (
                            "admin_set_require_whitelist"
                            | "admin_add_whitelisted_deployers"
                            | "admin_set_protocol_config"
                            | "admin_set_protocol_fee_recipient_account"
                            | "admin_set_protocol_fee_basis_points"
                            | "owner_set_admins"
                            | "owner_clear_admins"
                            | "owner_add_admins"
                            | "owner_remove_admins"
                        ):
                            if not match_pot_factory_pattern(receiver_id):
                                break
                            logger.info(f"updating configs.. {args_dict}")
                            await handle_set_factory_configs(args_dict, receiver_id)
                            break
                        case "create_list_with_registrations":
                            logger.info(f"creating list... {args_dict}, {action}")
                            if receiver_id != LISTS_CONTRACT:
                                break
                            await handle_new_list_and_reg(signer_id, receiver_id, status_obj, receipt)
                            break
                        # TODO: handle remove upvote

                except Exception as e:
                    logger.error(f"Error in indexer handler:\n{e}")
                    # with open("indexer_error.txt", "a") as file:
                    #     file.write(f"{e}\n")
            # logger.info(
            #     f"Time to process method calls for receipt {receipt_execution_outcome.receipt.receipt_id}: {time.time() - method_call_processing_start:.4f} seconds"
            # )
            # log_memory_usage("After processing method calls")
        # logger.info(
        #     f"Time to process shard {shard_index}: {time.time() - shard_start_time:.4f} seconds"
        # )
        # log_memory_usage(f"After processing shard {shard_index}")

    # logger.info(
    #     f"Total time to process streamer message: {time.time() - start_time:.4f} seconds"
    # )
    # log_memory_usage("End of handle_streamer_message")

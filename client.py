import argparse
import asyncio
import logging

from ipv8.configuration import (
    ConfigBuilder,
    Strategy,
    WalkerDefinition,
    default_bootstrap_defs,
)
from ipv8_service import IPv8
from ipv8.util import run_forever

from registration.registation_community import Lab3RegistrationCommunity
from community import BlockchainCommunity
from config import KEY_FILE

def parse_args():
    parser = argparse.ArgumentParser(description="Run Lab 3 PoW blockchain IPv8 node.")

    parser.add_argument(
        "-r",
        "--register",
        action="store_true",
        help="Register the blockchain community with the Lab 3 server before running.",
    )

    parser.add_argument(
        "-test",
        "--test",
        action="store_true",
        help="Run the local transaction bot for mempool/fork testing.",
    )

    parser.add_argument(
        "--test-interval",
        type=float,
        default=1.0,
        help="Seconds between locally generated test transactions.",
    )

    return parser.parse_args()


def init_ipv8():
    builder = ConfigBuilder().clear_keys().clear_overlays()

    builder.add_key("my node", "curve25519", KEY_FILE)

    # Community 1: used only for registering with the Lab 3 server
    builder.add_overlay(
        "Lab3RegistrationCommunity",
        "my node",
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
        default_bootstrap_defs,
        {},
        [],
    )

    # Community 2: actual PoW blockchain community
    builder.add_overlay(
        "BlockchainCommunity",
        "my node",
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
        default_bootstrap_defs,
        {},
        [],
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={
            "Lab3RegistrationCommunity": Lab3RegistrationCommunity,
            "BlockchainCommunity": BlockchainCommunity,
        },
    )

    # Suppress noisy IPv8 packet-handling errors from unrelated peers.
    logging.getLogger("Lab3RegistrationCommunity").setLevel(logging.CRITICAL)
    logging.getLogger("BlockchainCommunity").setLevel(logging.CRITICAL)

    return ipv8


async def main(register: bool) -> None:
    ipv8 = init_ipv8()

    await ipv8.start()

    register_community: Lab3RegistrationCommunity = ipv8.get_overlay(
        Lab3RegistrationCommunity
    )

    blockchain_community: BlockchainCommunity = ipv8.get_overlay(BlockchainCommunity)

    try:

        await blockchain_community.find_teammate_peers()
        blockchain_community.start_mining()

        if register:
            print("Register flag enabled. Finding server peer...")
            await register_community.find_server_peer()

            print("Registering blockchain community...")
            register_community.register_blockchain()

      

        await run_forever()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted by user. Exiting ... ")

    finally:
        blockchain_community.stop_mining()
        print("Stopping IPV8\n")
        await ipv8.stop()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        main(
            register=args.register,
            test=args.test,
            test_interval=args.test_interval,
        )
    )

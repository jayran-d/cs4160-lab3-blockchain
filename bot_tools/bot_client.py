import argparse
import asyncio
import logging
import sys
from pathlib import Path
from ipv8.util import run_forever
from ipv8_service import IPv8
from ipv8.configuration import (
    ConfigBuilder,
    Strategy,
    WalkerDefinition,
    default_bootstrap_defs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from bot_tools.bot_community import BotBlockchainCommunity
from bot_tools.transaction_bot import TransactionBot

KEY_FILE = str(REPO_ROOT / "keys" / "bot_identity_key.pem")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a blockchain node with the local transaction test bot."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between locally generated test transactions.",
    )
    return parser.parse_args()


def init_ipv8():
    builder = ConfigBuilder().clear_keys().clear_overlays()

    builder.add_key("bot node", "curve25519", KEY_FILE)

    builder.add_overlay(
        "BotBlockchainCommunity",
        "bot node",
        [WalkerDefinition(Strategy.RandomWalk, 10, {"timeout": 2.0})],
        default_bootstrap_defs,
        {},
        [],
    )

    ipv8 = IPv8(
        builder.finalize(),
        extra_communities={
            "BotBlockchainCommunity": BotBlockchainCommunity,
        },
    )

    # Suppress noisy IPv8 packet-handling errors from unrelated peers.
    logging.getLogger("BotBlockchainCommunity").setLevel(logging.CRITICAL)

    return ipv8


async def main(interval: float) -> None:
    ipv8 = init_ipv8()
    bot = None

    await ipv8.start()

    bot_blockchain_community: BotBlockchainCommunity = ipv8.get_overlay(
        BotBlockchainCommunity
    )

    print("Bot IPv8 public key:", bot_blockchain_community.own_public_key().hex())

    try:
        await bot_blockchain_community.find_teammate_peers()
        # The bot only generates and gossips test transactions; it does not mine.

        print(f"Starting transaction bot with interval {interval} seconds...")
        bot = TransactionBot(
            community=bot_blockchain_community,
            interval_seconds=interval,
        )

        bot.start()

        await run_forever()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted by user. Exiting ... ")

    finally:
        if bot is not None:
            bot.stop()
        bot_blockchain_community.stop_mining()
        print("Stopping IPV8\n")
        await ipv8.stop()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(interval=args.interval))

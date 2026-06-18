import argparse
import asyncio
import sys
from pathlib import Path

from ipv8.util import run_forever

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from client import init_ipv8
from community import BlockchainCommunity
from transaction_bot import TransactionBot


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


async def main(interval: float) -> None:
    ipv8 = init_ipv8()
    bot = None

    await ipv8.start()

    blockchain_community: BlockchainCommunity = ipv8.get_overlay(BlockchainCommunity)

    try:
        await blockchain_community.find_teammate_peers()
        # blockchain_community.start_mining()

        bot = TransactionBot(
            community=blockchain_community,
            interval_seconds=interval,
        )

        bot.start()

        await run_forever()

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nInterrupted by user. Exiting ... ")

    finally:
        if bot is not None:
            bot.stop()
        blockchain_community.stop_mining()
        print("Stopping IPV8\n")
        await ipv8.stop()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(interval=args.interval))

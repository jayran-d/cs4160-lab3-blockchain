import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import (
    DIFFICULTY_ADJUSTMENT_WINDOW_SIZE,
    TARGET_BLOCK_TIME_SECONDS,
)


SCENARIOS = {
    "fast": 3,
    "target": TARGET_BLOCK_TIME_SECONDS,
    "slow": 45,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mine a local synthetic chain and print adaptive difficulty changes."
    )
    parser.add_argument(
        "scenario",
        choices=SCENARIOS,
        help="Block timestamp pattern to feed into the real difficulty controller.",
    )
    parser.add_argument(
        "--blocks",
        type=int,
        default=12,
        help="Number of blocks to mine after genesis.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    interval = SCENARIOS[args.scenario]
    blockchain = Blockchain()
    timestamp = 0

    print(f"scenario={args.scenario}")
    print(f"target_block_time={TARGET_BLOCK_TIME_SECONDS}s")
    print(f"adjustment_window={DIFFICULTY_ADJUSTMENT_WINDOW_SIZE} blocks")
    print()

    for index in range(1, args.blocks + 1):
        parent_hash = blockchain.tip_hash()
        difficulty = blockchain.next_difficulty(parent_hash)
        parent_height = blockchain.height()
        timestamp += interval

        print(
            "before mining: "
            f"next_height={parent_height + 1}, "
            f"parent_height={parent_height}, "
            f"timestamp={timestamp}, "
            f"next_difficulty={difficulty}"
        )

        block = mine_block(
            prev_hash=parent_hash,
            transactions=[],
            timestamp=timestamp,
            difficulty=difficulty,
        )

        if block is None:
            raise RuntimeError("mining stopped unexpectedly")

        if not blockchain.add_block(block):
            raise RuntimeError("mined block was rejected")

        print(
            "accepted:      "
            f"height={blockchain.height()}, "
            f"difficulty={block.header.difficulty}, "
            f"nonce={block.header.nonce}, "
            f"hash={block.block_hash().hex()[:16]}..."
        )
        print()

    print("final_height=", blockchain.height())
    print("final_next_difficulty=", blockchain.next_difficulty())


if __name__ == "__main__":
    main()

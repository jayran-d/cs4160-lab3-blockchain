from collections.abc import Callable
from hashlib import sha256

from chain.block import Block, BlockHeader, compute_txs_hash
from chain.transaction import Transaction
from config import (
    BLOCK_DIFFICULTY,
    HASH_SIZE,
    MAX_POW_DIFFICULTY,
    MINING_STOP_CHECK_INTERVAL,
)
from chain.utils import u32_be, u64_be


def count_leading_zero_bits(data: bytes) -> int:
    """
    Count the number of leading zero bits in a byte string.

    Example:
        b"\\x00\\x7f..." starts with:
        - 8 zero bits from 0x00
        - then 1 zero bit from 0x7f = 01111111
        => total 9 leading zero bits
    """
    total = 0

    for byte in data:
        if byte == 0:
            total += 8
            continue

        for i in range(8):
            bit = (byte >> (7 - i)) & 1

            if bit == 0:
                total += 1
            else:
                return total

    return total


def valid_pow(block_hash: bytes, difficulty: int) -> bool:
    """
    Check whether block_hash satisfies the declared difficulty.

    Difficulty means:
        required number of leading zero bits in block_hash
    """
    if len(block_hash) != HASH_SIZE:
        print(
            f"Invalid block hash length: {len(block_hash)}. Expected {HASH_SIZE} bytes."
        )
        return False

    if difficulty < 0 or difficulty > MAX_POW_DIFFICULTY:
        print(
            f"Invalid difficulty: {difficulty}. "
            f"Must be between 0 and {MAX_POW_DIFFICULTY}."
        )
        return False

    if difficulty == 0:
        return True

    return int.from_bytes(block_hash, "big") < (1 << (MAX_POW_DIFFICULTY - difficulty))


def mine_block(
    prev_hash: bytes,
    transactions: list[Transaction],
    timestamp: int,
    difficulty: int = BLOCK_DIFFICULTY,
    should_stop: Callable[[], bool] | None = None,
    stop_check_interval: int = MINING_STOP_CHECK_INTERVAL,
) -> Block | None:
    if len(prev_hash) != HASH_SIZE:
        raise ValueError(f"prev_hash must be exactly {HASH_SIZE} bytes")

    if difficulty < 0 or difficulty > MAX_POW_DIFFICULTY:
        raise ValueError(f"difficulty must be between 0 and {MAX_POW_DIFFICULTY}")

    if stop_check_interval <= 0:
        raise ValueError("stop_check_interval must be positive")

    txs_hash = compute_txs_hash([tx.tx_hash() for tx in transactions])
    header_prefix = prev_hash + txs_hash + u64_be(timestamp) + u32_be(difficulty)
    nonce = 0

    while True:
        if (
            should_stop is not None
            and nonce % stop_check_interval == 0
            and should_stop()
        ):
            return None

        block_hash = sha256(header_prefix + u64_be(nonce)).digest()

        if valid_pow(block_hash, difficulty):
            header = BlockHeader(
                prev_hash=prev_hash,
                txs_hash=txs_hash,
                timestamp=timestamp,
                difficulty=difficulty,
                nonce=nonce,
            )
            return Block(header=header, transactions=transactions)

        nonce += 1

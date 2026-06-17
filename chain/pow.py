from chain.transaction import Transaction
from config import BLOCK_DIFFICULTY, HASH_SIZE


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

        # first nonzero byte
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

    if difficulty < 0 or difficulty > 256:
        print(f"Invalid difficulty: {difficulty}. Must be between 0 and 256.")
        return False

    return count_leading_zero_bits(block_hash) >= difficulty


def mine_block(
    prev_hash: bytes,
    transactions: list[Transaction],
    timestamp: int,
    difficulty: int = BLOCK_DIFFICULTY,
):

    from chain.block import Block, BlockHeader, compute_txs_hash

    if len(prev_hash) != HASH_SIZE:
        raise ValueError(f"prev_hash must be exactly {HASH_SIZE} bytes")

    txs_hash = compute_txs_hash([tx.tx_hash() for tx in transactions])
    nonce = 0

    while True:
        header = BlockHeader(
            prev_hash=prev_hash,
            txs_hash=txs_hash,
            timestamp=timestamp,
            difficulty=difficulty,
            nonce=nonce,
        )
        block = Block(header=header, transactions=transactions)

        if block.validate():
            return block

        nonce += 1

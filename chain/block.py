from chain.utils import sha256, u64_be, u32_be
from chain.transaction import Transaction
from dataclasses import dataclass
from config import HASH_SIZE, HEADER_SIZE

# Naming:
#   transactions  -> list[Transaction]
#   tx_hashes     -> list[bytes]
#   txs_hash      -> single bytes commitment -> sha256(tx1 + tx2 + ... + txn)


@dataclass
class BlockHeader:
    """
    Block header format.

    The packed header must be exactly 84 bytes:

        prev_hash   32 bytes
        txs_hash    32 bytes
        timestamp    8 bytes, uint64 big-endian
        difficulty   4 bytes, uint32 big-endian
        nonce        8 bytes, uint64 big-endian
    """

    prev_hash: bytes
    txs_hash: bytes
    timestamp: int
    difficulty: int
    nonce: int

    def pack(self) -> bytes:
        """
        Pack the block header into its exact binary format.
        """
        if len(self.prev_hash) != HASH_SIZE:
            raise ValueError("prev_hash must be exactly 32 bytes")

        if len(self.txs_hash) != HASH_SIZE:
            raise ValueError("txs_hash must be exactly 32 bytes")

        return (
            self.prev_hash
            + self.txs_hash
            + u64_be(self.timestamp)
            + u32_be(self.difficulty)
            + u64_be(self.nonce)
        )

    def block_hash(self) -> bytes:
        """
        Compute the 32-byte hash of this block header and check that the packed header is the correct length.
        """
        packed = self.pack()

        if len(packed) != HEADER_SIZE:
            raise ValueError("block header must be exactly 84 bytes")

        return sha256(packed)


@dataclass
class Block:
    """
    A block consists of:
    - a header
    - the transactions included in the block

    Locally mined blocks keep full Transaction objects. Blocks received from
    teammates may only carry transaction hashes, which is enough for lab grading.
    """

    header: BlockHeader
    transactions: list[Transaction]
    transaction_hashes: list[bytes] | None = None

    def block_hash(self) -> bytes:
        """
        Return the SHA-256 hash of the block header.
        """
        return self.header.block_hash()

    def prev_hash(self) -> bytes:
        """
        Return the previous block hash.
        """
        return self.header.prev_hash

    def tx_hashes(self) -> list[bytes]:
        """
        Return the list of transaction hashes in block order.
        """
        if self.transaction_hashes is not None:
            return self.transaction_hashes

        return [tx.tx_hash() for tx in self.transactions]

    def tx_hashes_bytes(self) -> bytes:
        """
        Return concatenated transaction hashes.

        This is exactly what the server expects in BlockResponsePayload.tx_hashes.
        Empty block => b"".
        """
        return b"".join(self.tx_hashes())

    def validate(self) -> bool:
        """
        Validate this block by checking:
        - prev_hash has correct size
        - txs_hash has correct size
        - txs_hash matches the included transactions

        This does NOT check whether the block links to a previous block.
        Chain-link and PoW validation should be done when appending to the chain.
        """
        if len(self.header.prev_hash) != HASH_SIZE:
            return False

        if len(self.header.txs_hash) != HASH_SIZE:
            return False

        expected_txs_hash = compute_txs_hash(self.tx_hashes())

        if expected_txs_hash != self.header.txs_hash:
            return False

        return True


def compute_txs_hash(tx_hashes: list[bytes]) -> bytes:
    """
    Compute the block body commitment.

    The lab requires:

        txs_hash = SHA256(tx_hash_1 || tx_hash_2 || ... || tx_hash_n)

    For an empty block:

        txs_hash = SHA256(b"")

    Since b"".join([]) is b"", this works for both normal and empty blocks.
    """

    if len(tx_hashes) == 0:
        return sha256(b"")

    return sha256(b"".join(tx_hashes))


def split_tx_hashes(tx_hashes: bytes) -> list[bytes]:
    """
    Split concatenated 32-byte transaction hashes from a block payload.
    """
    if len(tx_hashes) % HASH_SIZE != 0:
        raise ValueError("tx_hashes must be a multiple of 32 bytes")

    return [
        tx_hashes[index : index + HASH_SIZE]
        for index in range(0, len(tx_hashes), HASH_SIZE)
    ]


def create_genesis_block() -> Block:
    """
    Create the fixed genesis block.

    All 3 teammates must create EXACTLY the same genesis block.
    Otherwise the chains already disagree at height 0.

    We use:
    - prev_hash = 32 zero bytes
    - no transactions
    - txs_hash = SHA256(b"")
    - timestamp = 0
    - difficulty = 0
    - nonce = 0

    difficulty = 0 means the genesis block is always valid.
    """
    header = BlockHeader(
        prev_hash=b"\x00" * HASH_SIZE,
        txs_hash=compute_txs_hash([]),
        timestamp=0,
        difficulty=0,
        nonce=0,
    )

    return Block(
        header=header,
        transactions=[],
    )

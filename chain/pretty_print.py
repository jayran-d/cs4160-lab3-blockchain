from chain.block import Block
from chain.blockchain import Blockchain
from chain.transaction import Transaction


def short_hash(value: bytes, chars: int = 12) -> str:
    return value.hex()[:chars]


def format_transaction(tx: Transaction, index: int | None = None) -> str:
    prefix = f"Transaction {index}" if index is not None else "Transaction"

    return (
        f"{prefix}\n"
        f"  hash:      {tx.tx_hash().hex()}\n"
        f"  sender:    {short_hash(tx.sender_key)}...\n"
        f"  data:      {tx.data!r}\n"
        f"  timestamp: {tx.timestamp}\n"
        f"  signature: {short_hash(tx.signature)}...\n"
    )


def format_block(block: Block, height: int | None = None) -> str:
    title = f"Block height {height}" if height is not None else "Block"

    lines = [
        "=" * 70,
        title,
        "=" * 70,
        f"block_hash: {block.block_hash().hex()}",
        f"prev_hash:  {block.prev_hash().hex()}",
        f"txs_hash:   {block.header.txs_hash.hex()}",
        f"timestamp:  {block.header.timestamp}",
        f"difficulty: {block.header.difficulty}",
        f"nonce:      {block.header.nonce}",
        f"tx_count:   {len(block.transactions)}",
    ]

    if not block.transactions:
        lines.append("transactions: []")
    else:
        lines.append("transactions:")
        for i, tx in enumerate(block.transactions):
            lines.append(format_transaction(tx, i))

    return "\n".join(lines)


def print_block(block: Block, height: int | None = None) -> None:
    print(format_block(block, height))


def print_chain(blockchain: Blockchain) -> None:
    print("\n" + "#" * 70)
    print("CANONICAL BLOCKCHAIN")
    print("#" * 70)
    print(f"height:   {blockchain.height()}")
    print(f"tip_hash: {blockchain.tip_hash().hex()}")

    for height in range(blockchain.height() + 1):
        block = blockchain.get_block_at_height(height)
        if block is not None:
            print(format_block(block, height))


def print_mempool(blockchain: Blockchain) -> None:
    transactions = blockchain.mempool.get_all()

    print("\n" + "#" * 70)
    print("MEMPOOL")
    print("#" * 70)
    print(f"size: {len(transactions)}")

    if not transactions:
        print("transactions: []")
        return

    for i, tx in enumerate(transactions):
        print(format_transaction(tx, i))


def print_node_state(blockchain: Blockchain) -> None:
    print_chain(blockchain)
    print_mempool(blockchain)
from chain.transaction import Transaction
import threading


class Mempool:
    """
    Mempool stores transactions not yet included in a block.
        Key: tx_hash
        Value: Transaction
    """

    def __init__(self):
        self.transactions: dict[bytes, Transaction] = {}
        self.lock = threading.Lock()

    def add_transaction(self, tx: Transaction) -> bytes:
        """
        Add transaction to mempool.

        Returns the transaction hash.
        """
        tx_hash = tx.tx_hash()
        with self.lock:
            self.transactions[tx_hash] = tx
        
        return tx_hash

    def remove_transaction(self, tx_hash: bytes):
        with self.lock:
            self.transactions.pop(tx_hash, None)
            
    def contains_transaction(self, tx_hash: bytes) -> bool:
        return tx_hash in self.transactions

    def remove_multiple_transactions(self, transactions: list[Transaction]) -> None:
        """
        Remove multiple transactions at once that were included in a mined/appended block.
        """
        with self.lock:
            for tx in transactions:
                self.transactions.pop(tx.tx_hash(), None)

    def get_all_transactions(self) -> list[Transaction]:
        """
        Return current mempool transactions as a list.
        """
        with self.lock:
            return list(self.transactions.values())
        
    def size(self) -> int:
        return len(self.transactions)

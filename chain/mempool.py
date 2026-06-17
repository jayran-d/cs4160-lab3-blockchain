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

    def add(self, tx: Transaction) -> bytes:
        """
        Add transaction to mempool.

        Returns the transaction hash.
        """
        tx_hash = tx.tx_hash()
        with self.lock:
            self.transactions[tx_hash] = tx
        
        return tx_hash

    def remove(self, tx_hash: bytes):
        with self.lock:
            self.transactions.pop(tx_hash, None)

    def contains(self, tx_hash: bytes) -> bool:
        with self.lock:
            return tx_hash in self.transactions

    def remove_multiple(self, transactions: list[Transaction]) -> None:
        """
        Remove multiple transactions at once that were included in a mined/appended block.
        """
        with self.lock:
            for tx in transactions:
                self.transactions.pop(tx.tx_hash(), None)

    def get_all(self) -> list[Transaction]:
        """
        Return current mempool transactions as a list.
        """
        with self.lock:
            return list(self.transactions.values())
        
    def transactions_for_block(self, limit: int | None = None) -> list[Transaction]:
        transactions = self.get_all()
        if limit is None:
            return transactions
        return transactions[:limit]    
    
    def replace(self, transactions: list[Transaction]) -> None:
        with self.lock:
            self.transactions = {
                tx.tx_hash(): tx
                for tx in transactions
            }

    
    def get(self, tx_hash: bytes) -> Transaction | None:
        with self.lock:
            return self.transactions.get(tx_hash)

    def remove_transactions(self, transactions: list[Transaction]) -> None:
        with self.lock:
            for tx in transactions:
                self.transactions.pop(tx.tx_hash(), None)
        
    def __len__(self) -> int:
        return len(self.transactions)

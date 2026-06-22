from chain.blockchain import Blockchain
from chain.pow import mine_block


def mine_test_block(prev_hash: bytes, timestamp: int, difficulty: int):
    return mine_block(
        prev_hash=prev_hash,
        transactions=[],
        timestamp=timestamp,
        difficulty=difficulty,
    )


def test_block_with_too_low_declared_difficulty_is_rejected():
    chain = Blockchain()
    expected_difficulty = chain.next_difficulty()
    block = mine_test_block(
        prev_hash=chain.tip_hash(),
        timestamp=1,
        difficulty=expected_difficulty - 1,
    )

    assert not chain.add_block(block)
    assert chain.height() == 0


def test_block_with_too_high_declared_difficulty_is_rejected():
    chain = Blockchain()
    expected_difficulty = chain.next_difficulty()
    block = mine_test_block(
        prev_hash=chain.tip_hash(),
        timestamp=1,
        difficulty=expected_difficulty + 1,
    )

    assert not chain.add_block(block)
    assert chain.height() == 0


def test_block_with_expected_difficulty_is_accepted():
    chain = Blockchain()
    expected_difficulty = chain.next_difficulty()
    block = mine_test_block(
        prev_hash=chain.tip_hash(),
        timestamp=1,
        difficulty=expected_difficulty,
    )

    assert chain.add_block(block)
    assert chain.tip_hash() == block.block_hash()
    assert chain.height() == 1

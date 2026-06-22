from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import (
    BLOCK_DIFFICULTY,
    DIFFICULTY_ADJUSTMENT_WINDOW_SIZE,
    MAX_BLOCK_DIFFICULTY,
    MAX_DIFFICULTY_CHANGE_PER_BLOCK,
    MIN_BLOCK_DIFFICULTY,
    TARGET_BLOCK_TIME_SECONDS,
)


def mine_test_block(prev_hash: bytes, timestamp: int, difficulty: int):
    return mine_block(
        prev_hash=prev_hash,
        transactions=[],
        timestamp=timestamp,
        difficulty=difficulty,
    )


def add_timed_blocks(
    chain: Blockchain,
    timestamps: list[int],
    difficulty: int = BLOCK_DIFFICULTY,
) -> None:
    for timestamp in timestamps:
        block = mine_test_block(chain.tip_hash(), timestamp, difficulty)
        assert chain.add_block(block)


def test_next_difficulty_starts_from_initial_config_value():
    chain = Blockchain()

    assert chain.next_difficulty() == BLOCK_DIFFICULTY


def test_same_chain_history_gives_same_next_difficulty():
    timestamps = [
        3 * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    chain_a = Blockchain()
    chain_b = Blockchain()
    add_timed_blocks(chain_a, timestamps, BLOCK_DIFFICULTY)
    add_timed_blocks(chain_b, timestamps, BLOCK_DIFFICULTY)

    assert chain_a.next_difficulty() == chain_b.next_difficulty()
    assert chain_a.next_difficulty() == chain_a.next_difficulty()


def test_next_difficulty_rises_after_fast_blocks():
    chain = Blockchain()
    timestamps = [
        3 * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    add_timed_blocks(chain, timestamps, BLOCK_DIFFICULTY)

    assert chain.next_difficulty() == (
        BLOCK_DIFFICULTY + MAX_DIFFICULTY_CHANGE_PER_BLOCK
    )


def test_next_difficulty_falls_after_slow_blocks():
    chain = Blockchain()
    timestamps = [
        60 * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    add_timed_blocks(chain, timestamps, BLOCK_DIFFICULTY)

    assert chain.next_difficulty() == (
        BLOCK_DIFFICULTY - MAX_DIFFICULTY_CHANGE_PER_BLOCK
    )


def test_next_difficulty_stays_stable_near_target_block_time():
    chain = Blockchain()
    timestamps = [
        TARGET_BLOCK_TIME_SECONDS * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    add_timed_blocks(chain, timestamps, BLOCK_DIFFICULTY)

    assert chain.next_difficulty() == BLOCK_DIFFICULTY


def test_next_difficulty_clamps_to_minimum_difficulty():
    chain = Blockchain()
    timestamps = [
        60 * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    add_timed_blocks(chain, timestamps, BLOCK_DIFFICULTY)
    chain.tip().header.difficulty = MIN_BLOCK_DIFFICULTY

    assert chain.next_difficulty() == MIN_BLOCK_DIFFICULTY


def test_next_difficulty_clamps_to_maximum_difficulty():
    chain = Blockchain()
    timestamps = [
        3 * height
        for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
    ]
    add_timed_blocks(chain, timestamps, BLOCK_DIFFICULTY)
    chain.tip().header.difficulty = MAX_BLOCK_DIFFICULTY

    assert chain.next_difficulty() == MAX_BLOCK_DIFFICULTY

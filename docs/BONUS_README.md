# Adaptive Difficulty Bonus

## What The Feature Solves

With fixed Proof-of-Work difficulty, block time depends directly on available
hashpower. If mining becomes faster, blocks arrive too quickly. If mining becomes
slower, blocks arrive too slowly.

The adaptive difficulty feature makes every node calculate the required
difficulty from the recent chain history. This gives two important properties:

- honest miners mine with the expected difficulty;
- received blocks are rejected if they declare a different difficulty.

So difficulty is not just miner preference. It is part of block validation.

## How The Next Difficulty Is Calculated

The calculation happens in `Blockchain.next_difficulty()`.

For a new block on top of a parent block, the node does this:

1. Walk backward from the parent block over the last
   `DIFFICULTY_ADJUSTMENT_WINDOW_SIZE` blocks.
2. For each block, calculate the timestamp interval:

   ```text
   interval = current_block.timestamp - parent_block.timestamp
   ```

3. Clamp every interval into a reasonable range:

   ```text
   raw interval 1s   -> use 3s
   raw interval 15s  -> use 15s
   raw interval 300s -> use 60s
   ```

   This avoids one strange timestamp having a huge effect.

4. Take the median of the clamped intervals.

   We use the median instead of the average because one bad value affects an
   average much more strongly. For example:

   ```text
   intervals = [14, 15, 15, 16, 300]
   average   = 72
   median    = 15
   ```

5. Compare the median with the target block time.

   Our target is 15 seconds. We also use a tolerance band of 20%.

   ```text
   lower bound = 15 * (1 - 0.20) = 12 seconds
   upper bound = 15 * (1 + 0.20) = 18 seconds
   ```

   So:

   ```text
   median < 12s    -> blocks are too fast  -> increase difficulty
   median > 18s    -> blocks are too slow  -> decrease difficulty
   12s to 18s      -> close enough         -> keep difficulty
   ```

   The tolerance band prevents the chain from constantly changing difficulty
   because of normal PoW randomness.

6. Convert the timing difference into a difficulty step.

   Difficulty is measured in leading-zero bits. One extra bit roughly doubles the
   expected work. That is why we use `log2`.

   Example with fast blocks:

   ```text
   target = 15s
   observed median = 3s
   ratio = 15 / 3 = 5
   ceil(log2(5)) = 3
   max allowed step = 2
   final step = +2
   ```

   So if the current difficulty is 16, the next difficulty becomes 18.

7. Clamp the final difficulty between `MIN_BLOCK_DIFFICULTY` and
   `MAX_BLOCK_DIFFICULTY`.

This means the result is deterministic: the same parent chain and same config
always produce the same next difficulty.

## Timestamp Protection

The difficulty calculation uses block timestamps, so timestamps need basic
protection.

A block is rejected if:

- its timestamp is not greater than its parent timestamp;
- its timestamp is behind the recent median chain timestamp;
- its timestamp is too far in the future.

This matters because a bad timestamp can otherwise trick the controller. A very
large future timestamp could make blocks look too slow and push difficulty down.
Very compressed timestamps could make blocks look too fast and push difficulty
up.

We do not try to solve every possible timestamp lie. Instead, we reject obvious
bad timestamps and clamp the values used by the controller. That keeps the design
simple while stopping one extreme timestamp from dominating difficulty.

## Miner And Block Validation

When mining locally, the miner asks the chain for the expected difficulty:

```python
difficulty = blockchain.next_difficulty(parent_hash)
```

The mined block uses that value in its header.

When receiving a block from another peer, the node recomputes the expected value
from the parent chain:

```python
expected = blockchain.next_difficulty(parent_hash)
```

If the block declares a different difficulty, it is rejected. Proof-of-Work is
still checked normally after that: the block hash must satisfy the declared
difficulty, and the declared difficulty must be the expected one.

This prevents peers from mining cheap blocks with arbitrary low difficulty.

## Comparison With Other Approaches

Bitcoin-style retargeting keeps difficulty stable for a long period and then
retargets. That is stable, but it reacts slowly. The useful idea we keep from
Bitcoin is that difficulty and timestamp validity are consensus rules, not local
miner choices. Reference: [Bitcoin block chain developer reference](https://developer.bitcoin.org/reference/block_chain.html).

ASERT-style difficulty adjustment, used by Bitcoin Cash, updates difficulty
exponentially relative to an anchor point. It is smoother and more principled
than a small moving window, but it also needs more careful parameter tuning and
integer math. Reference: [Bitcoin Cash ASERT specification](https://upgradespecs.bitcoincashnode.org/2020-11-15-asert/).

Ethereum proof of stake does not adjust mining difficulty because it does not use
PoW mining. It uses fixed time slots and validator selection instead. This is a
different consensus model, but it shows another way to control block timing.
Reference: [Ethereum proof-of-stake docs](https://ethereum.org/developers/docs/consensus-mechanisms/pos/).

Other adaptive PoW algorithms, such as LWMA, EMA, ASERT, or PID-like controllers,
can be smoother or more accurate. The tradeoff is complexity. Our design is less
advanced, but it is easy to inspect, deterministic, and directly tested.

## Tradeoffs

Responsiveness vs stability:

- Smaller windows react faster.
- Larger windows are less noisy.
- Our tolerance band and max-step cap reduce oscillation.

Timestamp resistance vs simplicity:

- Median intervals, interval clamping, and future-time rejection make one bad
  timestamp much less dangerous.
- This is not as strong as a protocol where peers vote on observed receive time.
- We avoid changing the network protocol.

Accuracy vs implementation size:

- We use recent block times plus the parent difficulty.
- A more advanced controller could use cumulative work over the full window.
- That would be more accurate when difficulty changes inside the window, but also
  more complex.

## Small Experiment

The table below shows one continuous flow using the same rules as the
implementation. Each row represents one adjustment window. The blocks in that
window are mined using the current difficulty. After the window, the next
difficulty is calculated from the median block interval.

Config used:

```text
initial difficulty = 16
target block time = 15s
window size = 5
max difficulty step = 2
tolerance band = 12s to 18s
```

| Window | Intervals in window | Difficulty used for those blocks | Median interval | Change | Next difficulty |
| --- | --- | ---: | ---: | ---: | ---: |
| Fast window 1 | `3, 3, 3, 3, 3` | 16 | 3s | +2 | 18 |
| Fast window 2 | `3, 3, 3, 3, 3` | 18 | 3s | +2 | 20 |
| Near target | `14, 15, 15, 16, 15` | 20 | 15s | 0 | 20 |
| Slow window 1 | `60, 60, 60, 60, 60` | 20 | 60s | -2 | 18 |
| Slow window 2 | `60, 60, 60, 60, 60` | 18 | 60s | -2 | 16 |
| Near target again | `15, 16, 14, 15, 15` | 16 | 15s | 0 | 16 |

This shows the intended behavior:

- when blocks are repeatedly too fast, difficulty rises gradually;
- when blocks are close to the target, difficulty stays stable;
- when blocks are repeatedly too slow, difficulty falls gradually;
- changes are capped, so the controller does not jump wildly.

## Limitations

This is not a production-grade difficulty adjustment algorithm. It does not use
ASERT anchors, peer-observed timestamps, or cumulative work over the full window.
It also relies on all honest nodes using the same constants from `config.py`.

The mechanism is still suitable for the bonus because it demonstrates the core
properties:

- same chain history gives the same next difficulty;
- miners use the computed difficulty;
- received blocks cannot declare arbitrary difficulty;
- fast blocks increase difficulty;
- slow blocks decrease difficulty;
- near-target blocks keep difficulty stable;
- invalid timestamps are rejected before they affect difficulty.

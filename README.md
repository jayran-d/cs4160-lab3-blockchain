# CS4160 Lab 3 Blockchain

This repository contains our implementation of the Lab 3 blockchain node. This Readme only explains how our implementation is structured, what design choices we made,
and how to run it.

## What this implementation does

Each group member runs one IPv8 node. Together, the three nodes form one
Proof-of-Work blockchain network.

The node:

- discovers the other two group members through IPv8
- mines blocks on top of the current best chain
- accepts valid signed transactions from the Lab 3 server
- shares accepted transactions with teammates
- shares newly mined blocks with teammates
- validates received blocks before using them
- switches to a longer valid fork when needed
- answers the Lab 3 server's chain-height and block queries

On shutdown, the client prints the final local chain so the current state can be
inspected.

## Implementation choices

The code is split into small components so the core blockchain logic can be
tested without running a live IPv8 network.

| Component              | Responsibility                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| `client.py`            | Starts IPv8, starts mining, and optionally registers with the Lab 3 server.                |
| `community.py`         | Handles blockchain network messages, peer filtering, transaction gossip, and block gossip. |
| `registration/`        | Handles registration of our blockchain community with the Lab 3 server.                    |
| `chain/block.py`       | Defines the block header, block hash, transaction commitment, and genesis block.           |
| `chain/transaction.py` | Defines transaction hashing and signature verification.                                    |
| `chain/mempool.py`     | Stores transactions waiting to be mined.                                                   |
| `chain/miner.py`       | Periodically mines blocks from the mempool.                                                |
| `chain/blockchain.py`  | Stores blocks, validates new blocks, handles forks, and tracks the canonical chain.        |
| `chain/pow.py`         | Implements Proof-of-Work mining and validation.                                            |
| `bot_tools/`           | Sandbox overlay and transaction bot for testing without touching the production chain.     |
| `tests/`               | Contains unit and simulation tests for the main behavior.                                  |

Important design decisions:

- We use a fixed genesis block so all three nodes start from the same chain.
- We only accept server messages from the configured Lab 3 server public key.
- We only accept teammate gossip from the configured teammate public keys.
- Blocks are validated before they are added to local state.
- Forks are resolved using the longest-chain rule.
- Orphan blocks are stored until their parent block becomes known.
- When the canonical chain changes, the mempool is updated so transactions from
  replaced blocks are not lost.

These choices make the node more stable during the automated grading attempt,
where all three nodes must agree on the same confirmed chain.

## Setup

Use Python 3.10 or newer.

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place your IPv8 private key at the path configured in `config.py`:

```text
keys/lab_identity_key.pem
```

Do not commit private keys.

Before running, check the values in `config.py`:

- `GROUP_ID`
- `BLOCKCHAIN_COMMUNITY_ID_HEX`
- `REGISTER_SERVER_PUBLIC_KEY_HEX`
- `MEMBER_PUBLIC_KEYS_HEX`
- `KEY_FILE`

## Running a node

Start one node with:

```bash
source .venv/bin/activate
python client.py
```

All three group members should run the node at the same time. The client first
waits until the configured teammates are found. After that, mining starts
automatically.

Stop the node with:

```text
Ctrl+C
```

## Registering with the server

When the three nodes are online and have found each other, one group member can
run:

```bash
source .venv/bin/activate
python client.py --register
```

This registers the configured blockchain community with the Lab 3 server. If the
server check fails because nodes were offline or not synchronized yet, keep the
nodes running and register again.

## Sandbox testing with the transaction bot

To exercise mempool, mining, and gossip behavior without touching the
production chain used for grading, run the node with `--test`:

```bash
source .venv/bin/activate
python client.py --test
```

This starts a second overlay (`BotBlockchainCommunity`, its own `community_id`
configured in `config.py`) alongside the real one. A `TransactionBot` generates
signed test transactions on an interval (`--test-interval`, default 1 second)
and gossips them to the other teammates' sandbox overlays. All three group
members should pass `--test` for the sandbox chain to converge. On shutdown,
both the production chain and the sandbox chain are printed separately.

You can also run just the sandbox overlay, without the production chain, using
`bot_tools/bot_client.py`:

```bash
source .venv/bin/activate
python bot_tools/bot_client.py
```

## Running tests

Run all local tests with:

```bash
source .venv/bin/activate
pytest
```

The tests cover the core blockchain behavior, including block formatting,
transaction validation, Proof-of-Work, mempool behavior, mining, gossip handling,
fork handling, and network simulation behavior.

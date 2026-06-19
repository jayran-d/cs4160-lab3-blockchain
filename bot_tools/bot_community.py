from community import BlockchainCommunity
from config import BOT_COMMUNITY_ID_HEX


class BotBlockchainCommunity(BlockchainCommunity):
    """
    Sandbox blockchain overlay for the transaction-bot test setup.

    Reuses all of BlockchainCommunity's mining/gossip/fork logic but runs on
    its own community_id, so injected test transactions never touch the
    production chain used for grading.
    """

    community_id = bytes.fromhex(BOT_COMMUNITY_ID_HEX)

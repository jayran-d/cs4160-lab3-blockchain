from community import BlockchainCommunity
from config import BOT_COMMUNITY_ID_HEX


class BotBlockchainCommunity(BlockchainCommunity):
    """
    Blockchain community variant used by the local transaction bot for testing.
    """

    community_id = bytes.fromhex(BOT_COMMUNITY_ID_HEX)

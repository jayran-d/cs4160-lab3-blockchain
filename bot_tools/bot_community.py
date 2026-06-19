from community import BlockchainCommunity
from config import BLOCKCHAIN_COMMUNITY_ID_HEX


class BotBlockchainCommunity(BlockchainCommunity):
    """
    Blockchain community variant used by the local transaction bot for testing.
    """

    community_id = bytes.fromhex(BLOCKCHAIN_COMMUNITY_ID_HEX)

import base64

P2P_PORT = 60337
RPC_PORT = 61337

UNIT = 10 ** 6

BLOCK_TIME = 30
LWMA_WINDOW = 90

SYNC_INTERVAL = BLOCK_TIME // 2
COMPRESSION_LEVEL = 19  # Min: 0 - Rec: 3~6 - Max: 19

REDUCTION_FACTOR = 2 ** 20

SEEDS = ["192.168.0.13"]
GENESIS_HASH = base64.b64decode(
        "Qh5YJuWnbXBU/xvQ6nJ8JkHrIzjJgbdi5xKUKmYPUvj5YuZAWSDNhAwpXd1lTHUag1WJVilUN"
        "/OzZD4mRLuzMvnKqUwHO1+WA7I6+CO8b+3AHNfkDx725tunk+TxgUUFjDkRmhdwStoR+9JvL6L"
        "/0kFOesF4WBS6Bwi7bdDNFB5TfWprlS4bZG/oYsPJjxBGUlwO3EWulM6zjt0H3TOk0DwKze8eNQfB6"
        "/mpTe0VHP39+vhFXw2d8ttxkfdRadr0iLFeK2QZ/K8DPEJxZ9qYg6aSQ"
        "+kBlaTw3CawyiMSPWKVtcSRW7iGEIogbViGx4PvdwG38wAx/D/qR+78qKybMA=="
        ).decode(errors='ignore')


def reward_function(block_index, block_size, old_mean):
    size_factor = block_size / min(1, abs(block_size - old_mean)) ** 1.5
    index_reduction = (1 - 1 / REDUCTION_FACTOR) ** int(block_index)
    return size_factor * index_reduction * UNIT

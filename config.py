P2P_PORT = 60337
RPC_PORT = 61337

UNIT = 10 ** 6

BLOCK_TIME = 30
LWMA_WINDOW = 90

REDUCTION_FACTOR = 2 ** 20

SEEDS = ["192.168.0.13"]


def reward_function(block_index, block_size, old_mean):
    size_factor = block_size / min(1, abs(block_size - old_mean)) ** 1.5
    index_reduction = (1 - 1 / REDUCTION_FACTOR) ** int(block_index)
    return size_factor * index_reduction * UNIT

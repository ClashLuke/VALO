import math

P2P_PORT = 60337
RPC_PORT = 61337

UNIT = 10 ** 6


def reward_function(block_index, block_size, old_mean):
    size_factor = block_size / min(1, abs(block_size - old_mean)) ** 1.5
    return size_factor * UNIT / math.log2(2 + block_index)

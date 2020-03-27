import config


def bytes_to_int(bytes_obj: bytes):
    return int.from_bytes(bytes_obj, byteorder='little')


def next_difficulty(timestamps: list, target_difficulties: list):
    # Zawy's LWMA difficulty algorithm
    if len(timestamps) < config.LWMA_WINDOW:
        return 2

    adjustment_factor = (config.LWMA_WINDOW + 1) / 2 * 0.998 ** (
            500 / config.LWMA_WINDOW) * config.BLOCK_TIME
    target_sum = sum(target_difficulties)
    target = sum((timestamps[i] - timestamps[i - 1]
                  ) * i for i in range(1, 1 + config.LWMA_WINDOW))

    # Keep target reasonable in case strange solvetimes occurred.
    if target < config.BLOCK_TIME * adjustment_factor // 3:
        target = config.BLOCK_TIME * adjustment_factor // 3
    return target * target_sum // adjustment_factor // config.BLOCK_TIME ** 2

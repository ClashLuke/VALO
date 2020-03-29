import config


def bytes_to_int(bytes_obj: bytes):
    return int.from_bytes(bytes_obj, byteorder='little')


def next_difficulty(timestamps: list, target_difficulties: list):
    # Zawy's LWMA difficulty algorithm
    adjustment_factor = int((config.LWMA_WINDOW + 1) / 2 * (0.998 ** (
            500 / config.LWMA_WINDOW)) * config.BLOCK_TIME)
    target_sum = sum(target_difficulties[1:])
    solve_time_lwma = sum((timestamps[i] - timestamps[i - 1]
                           ) * i for i in range(1, 1 + config.LWMA_WINDOW))
    # Keep target reasonable in case strange solvetimes occurred.
    if solve_time_lwma < config.BLOCK_TIME * adjustment_factor // 3:
        solve_time_lwma = config.BLOCK_TIME * adjustment_factor // 3
    val = target_sum * adjustment_factor // solve_time_lwma
    return val


def ping():
    return "pong"


def reply_wrapper(function):
    def wrapped_function(_, message: dict):
        request_type = message.pop('key')
        value = function(**message)
        return {'key': 'reply', 'request_type': request_type, 'data': value}

    return wrapped_function

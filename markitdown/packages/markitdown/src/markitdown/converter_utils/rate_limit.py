import random
import time


def handle_rate_limit(index: int, maximum_backoff: int = 10000):
    time_to_sleep = min((2 ** index) * 1000 + random.randint(0, 1000), maximum_backoff)

    time.sleep(time_to_sleep / 1000)

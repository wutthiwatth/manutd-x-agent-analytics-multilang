import argparse
import signal
import sys
import time

from .analytics import run_analytics_cycle
from .config import config
from .mongo import close_mongo

_shutdown = False


def handle_signal(signum, _frame):
    global _shutdown
    name = signal.Signals(signum).name
    print(f'[analytics] Received {name}. Shutting down...', flush=True)
    _shutdown = True


def sleep_interruptible(seconds: int) -> None:
    slept = 0
    while slept < seconds and not _shutdown:
        time.sleep(min(1, seconds - slept))
        slept += 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Man Utd X analytics-only worker')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run one full drain cycle until no pending tweets, then exit',
    )
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        try:
            run_analytics_cycle()
        except Exception as exc:
            print(f'[analytics] First cycle failed: {exc}', file=sys.stderr, flush=True)
            if args.once:
                return 1

        if args.once:
            return 0

        interval_seconds = config.analytics_interval_minutes * 60
        print(f'[analytics] Running drain cycle every {config.analytics_interval_minutes} minute(s).', flush=True)

        while not _shutdown:
            sleep_interruptible(interval_seconds)
            if _shutdown:
                break

            try:
                run_analytics_cycle()
            except Exception as exc:
                print(f'[analytics] Cycle failed: {exc}', file=sys.stderr, flush=True)

        return 0
    finally:
        close_mongo()


if __name__ == '__main__':
    raise SystemExit(main())

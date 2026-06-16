import argparse
import signal
import sys
import time

from .analytics import run_analytics_once
from .config import config
from .mongo import close_mongo

_shutdown = False


def handle_signal(signum, _frame):
    global _shutdown
    name = signal.Signals(signum).name
    print(f'[analytics] Received {name}. Shutting down...', flush=True)
    _shutdown = True


def main() -> int:
    parser = argparse.ArgumentParser(description='Man Utd X analytics-only worker')
    parser.add_argument('--once', action='store_true', help='Run one analytics batch and exit')
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        try:
            run_analytics_once()
        except Exception as exc:
            print(f'[analytics] First run failed: {exc}', file=sys.stderr, flush=True)
            if args.once:
                return 1

        if args.once:
            return 0

        interval_seconds = config.analytics_interval_minutes * 60
        print(f'[analytics] Running every {config.analytics_interval_minutes} minute(s).', flush=True)

        while not _shutdown:
            slept = 0
            while slept < interval_seconds and not _shutdown:
                time.sleep(min(1, interval_seconds - slept))
                slept += 1

            if _shutdown:
                break

            try:
                run_analytics_once()
            except Exception as exc:
                print(f'[analytics] Run failed: {exc}', file=sys.stderr, flush=True)

        return 0
    finally:
        close_mongo()


if __name__ == '__main__':
    raise SystemExit(main())

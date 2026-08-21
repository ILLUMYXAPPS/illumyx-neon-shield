import argparse
from pathlib import Path

from copyright_online_sweep import OnlineCopyrightSweep, SweepTarget


def main():
    parser = argparse.ArgumentParser(description="ILLUMYX Neon Shield CLI")
    parser.add_argument("--message", type=str, default="⚡ Neon Bolt CLI running!", help="Message to display")
    parser.add_argument("--copyright-title", type=str, help="Build public-search targets for an ILLUMYX work")
    parser.add_argument("--work-id", type=str, default="cli-work", help="Stable work identifier")
    parser.add_argument("--export-sweep", type=Path, help="Export a timestamped candidate-match transcript")
    args = parser.parse_args()

    if args.copyright_title:
        target = SweepTarget(args.work_id, args.copyright_title)
        sweep = OnlineCopyrightSweep()
        print("ONLINE COPYRIGHT SWEEP TARGET")
        for url in sweep.search_urls(target):
            print(url)
        if args.export_sweep:
            print(f"Transcript: {sweep.export_transcript(args.export_sweep)}")
        return

    print(args.message)


if __name__ == "__main__":
    main()

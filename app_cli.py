import argparse

def main():
    parser = argparse.ArgumentParser(description="YourApp CLI v1")
    parser.add_argument("--message", type=str, default="⚡ Neon Bolt CLI running!", help="Message to display")
    args = parser.parse_args()
    print(args.message)

if __name__ == "__main__":
    main()

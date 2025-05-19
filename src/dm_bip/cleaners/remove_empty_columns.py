#!/usr/bin/env python3

import argparse
import signal
import sys

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser(description="Clean a TSV file by dropping columns where all values are NaN.")
    parser.add_argument(
        "input_file",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Path to the input TSV file or stdin",
    )
    parser.add_argument(
        "-o", "--output", type=argparse.FileType("w"), default=sys.stdout, help="Path to the output TSV file or stdout"
    )
    args = parser.parse_args()

    return args


def remove_empty_columns(df, output):
    df = pd.read_csv(df, sep="\t")  # Read TSV
    df.dropna(axis=1, how="all", inplace=True)  # Drop columns where all values are NaN

    try:
        df.to_csv(output, sep="\t", index=False)  # Save back as TSV
    except BrokenPipeError:
        sys.stderr.close()


def main():
    args = parse_args()
    remove_empty_columns(args.input_file, args.output)


if __name__ == "__main__":
    # Handle SIGPIPE to prevent broken pipe errors
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()

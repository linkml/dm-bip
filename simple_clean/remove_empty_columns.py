#!/usr/bin/env python3

import pandas as pd
import argparse
import sys
import signal

def main():
    parser = argparse.ArgumentParser(description="Clean a TSV file by dropping columns where all values are NaN.")
    parser.add_argument("input_file", nargs="?", type=argparse.FileType('r'), default=sys.stdin, help="Path to the input TSV file or stdin")
    parser.add_argument("-o", "--output", type=argparse.FileType('w'), default=sys.stdout, help="Path to the output TSV file or stdout")
    args = parser.parse_args()

    df = pd.read_csv(args.input_file, sep="\t")  # Read TSV
    df.dropna(axis=1, how="all", inplace=True)  # Drop columns where all values are NaN

    try:
        df.to_csv(args.output, sep="\t", index=False)  # Save back as TSV
    except BrokenPipeError:
        sys.stderr.close()

if __name__ == "__main__":
    # Handle SIGPIPE to prevent broken pipe errors
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()

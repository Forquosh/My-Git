#!/bin/bash
# This script runs the Git implementation in Python.

set -e  # Exit early if any commands fail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <command> [options]"
    echo "Available commands: init, clone, hash-object, cat-file, write-tree, commit-tree, ls-tree"
    exit 1
fi

PYTHONPATH=$(dirname $0) exec python3 -m app.main "$@"

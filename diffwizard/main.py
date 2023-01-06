import subprocess
import os
import json
import re

def get_diff(folder: str = os.getcwd()):
    """Get the diff between current and previous commit
    """
    os.chdir(folder)
    diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD"])
    diff = diff.decode("utf-8")


    return diff

def parse_diff(diff: str):
    """Parse a git diff into a list of files and changes
    """
    diff = diff.split("diff --git")
    diff = [i for i in diff if i != ""]
    return diff


def split_long_diff(diff: str, max_length: int = 2000):
    """Split a diff into multiple diffs of max_length, first on file, then on lines
    """
    if len(diff) < max_length:
        return [diff]
    # Split on files if diff too long
    diffs = parse_diff(diff)
    new_diffs = []
    for d in diffs:
        if len(d) > max_length:
            stop_index=0
            i=0
            while len(d) > max_length:
                max_i = min((i+1)*max_length, len(d))
                new_d = d[stop_index:max_i]
                stop_index = new_d.rfind("/n")
                new_d = new_d[:stop_index]
                new_diffs.append(new_d)
                i+=1
        else:
            new_diffs.append(d)
    return new_diffs

if __name__ == "__main__":
    diff = get_diff()
    diffs = split_long_diff(diff)
    print(diffs)

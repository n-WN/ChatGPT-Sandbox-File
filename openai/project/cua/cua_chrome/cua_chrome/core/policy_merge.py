"""
merge chrome enterprise policies copied under $CHROMIUM_POLICY_DIR
creates a single merged json file with original backups under .policy_merge
http://go/docs-link/cua-chrome-policy-merge
"""

import glob
import json
import re
import sys
import typing
from pathlib import Path

AnyDict = dict[str, typing.Any]

OUTPUT_FILENAME = "000_policy_merge.json"
"""
The name of the output file that will contain the merged policies.
We specifically allow overwriting this file so you can merge policies
in a second pass, e.g. in response to a policy change.
"""


def main(*, path: Path, merge_keys: list[str]) -> None:
    print(f"{path=}")
    print(f"{merge_keys=}")

    path = path.expanduser()
    merged_path = Path(path) / OUTPUT_FILENAME

    if not path.exists():
        raise ValueError(f"{path=} does not exist")

    # ensure the .policy_merge directory exists
    backup_dir = path / ".policy_merge"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # ensure glob of filename is sorted as one would expect
    file_list = list(glob.glob(f"{str(path)}/*"))
    file_list.sort(key=natural_sort_key)

    policy_list: list[AnyDict] = []
    for filename in file_list:
        print(f"  {filename}")
        file_path = Path(filename)

        with open(file_path, "r") as f:
            policy_list.append(json.load(f))

        # move file_path to nested .policy_merge dir
        new_file_path = backup_dir / file_path.name
        file_path.rename(new_file_path)

    merged: AnyDict = dict()
    merge_keys_set = set(merge_keys)
    for policy in policy_list:
        # move policies to nested .policy_merge dir
        merged = deep_merge(merged, policy, merge_keys_set=merge_keys_set)

    # write merged policy to path
    with open(merged_path, "w") as f:
        json.dump(merged, f, indent=2)

    if not merged_path.exists():
        raise ValueError(f"{merged_path} must exist")


def deep_merge(a: AnyDict, b: AnyDict, *, merge_keys_set: set[str]) -> AnyDict:
    result = a.copy()
    for key, value in b.items():
        # recurse if both values are dictionaries
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            if key in merge_keys_set:
                result[key] = deep_merge(result[key], value, merge_keys_set=merge_keys_set)
            else:
                result[key] = value
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            if key in merge_keys_set:
                for item in value:
                    if item not in result[key]:
                        result[key].append(item)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


# splits the string into numeric and non-numeric parts for sorting
def natural_sort_key(item: typing.Any) -> list[int | str | float]:
    # ensure None keys always sort last
    if item is None:
        return [float("inf")]

    item_str = str(item)

    return [
        # convert to int if digit
        int(text) if text.isdigit() else text
        for text in re.split(RE_DIGIT, item_str)
    ]


RE_DIGIT = re.compile(r"(\d+)")


if __name__ == "__main__":
    [command, *arg_list] = sys.argv

    arg_separator = "="
    path = None
    merge_keys = None
    for arg in arg_list:
        if arg_separator in arg:
            [key, value] = arg.split(arg_separator)
            if not value:
                raise ValueError(f"{key} missing value")
            if key == "path":
                path = Path(value)
            elif key == "merge_keys":
                merge_keys = value.split(",")

    if path is None:
        raise ValueError("path is required")

    if merge_keys is None:
        raise ValueError("merge_keys is required")

    main(path=path, merge_keys=merge_keys)

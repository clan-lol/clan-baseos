import argparse
import shlex
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("--reviewers", nargs="*", default=[])
parser.add_argument("--no-review", action="store_true")
parser.add_argument("args", nargs="*")
args = parser.parse_args()

# complain if neither --reviewers nor --no-review is given
if not args.reviewers and not args.no_review:
    parser.error("either --reviewers or --no-review must be given")

cmd = [
    "tea-create-pr",
    "origin",
    "upstream",
    "main",
    "--assignees",
    ",".join(["clan-bot", *args.reviewers]),
    *(["--labels", "needs-review"] if not args.no_review else []),
    *args.args,
]

print("Running:", shlex.join(cmd))

subprocess.run(cmd, check=True)

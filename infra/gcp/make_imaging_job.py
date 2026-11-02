"""Write the Cloud Batch job spec for H-0012 (infra/gcp/imaging_tile.py). DESIGN: not submitted.

    python3 infra/gcp/make_imaging_job.py h0012a tiles_h0012.txt 332 2 25 <git-sha>
    python3 infra/gcp/make_imaging_job.py h0012b tiles_h0012b.txt 334 2 25 <sha> --granted --code-dir h0012b \
        --bright bright_sources_10mpc.csv --known known_positions.csv          # v2

args: job name, tile list (in gs://.../code/), number of tiles, tiles per task, parallelism, code sha.
v2 options: --code-dir D puts the code AND every input file under gs://.../code/D/ (h0012a read the tile list
and targets from code/ and the code from code/h0012/); --bright / --known pass the runner's v2 inputs.
The job is written with ODDSKY_UNWISE_PERMISSION unset: the task exits (status 3) until a human edits
the spec to "granted" after A. Meisner has agreed to the ~330 GB pull. parallelism 25 x 2 connections
per task keeps the load on NERSC at <= 50 concurrent downloads; lower it if asked.
"""

import json
import sys

name, tile_list, n_tiles, per_task, parallelism, sha = (sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]),
                                                       int(sys.argv[5]), sys.argv[6])


def opt(flag):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else None


code_dir, bright, known = opt("--code-dir"), opt("--bright"), opt("--known")
CODE = "/mnt/disks/oddsky/code"
src = f"{CODE}/{code_dir}" if code_dir else f"{CODE}/h0012"
inp = f"{CODE}/{code_dir}" if code_dir else CODE
# Permission: A. Meisner agreed by phone with Alan Shortz on 2026-11-01 to Oddsky using the neo11 epochal coadds for this
# search (see hunts/H-0012/README.md, provenance). Pass --granted to write the spec with the gate open.
permission = "granted" if "--granted" in sys.argv else "NOT-YET"
tasks = -(-n_tiles // per_task)
cmd = ("set -euo pipefail; PIP_DISABLE_PIP_VERSION_CHECK=1 pip install -q --root-user-action=ignore --no-cache-dir "
       "numpy==2.* scipy==1.* 'astropy>=7' pandas==2.* pyarrow==21.* httpx && "
       f"export PYTHONPATH={src}/src && "
       f"python -u {src}/infra/gcp/imaging_tile.py --tiles {inp}/{tile_list} "
       f"--targets {inp}/targets_10mpc.csv --tiles-per-task {per_task} "
       + (f"--bright {inp}/{bright} " if bright else "") + (f"--known {inp}/{known} " if known else "")
       + f"--out /mnt/disks/oddsky/runs/{name} --code-version {sha}")
job = {
    "taskGroups": [{
        "taskCount": tasks, "parallelism": parallelism,
        "taskSpec": {
            "runnables": [{"container": {"imageUri": "python:3.12-slim", "entrypoint": "/bin/bash", "commands": ["-c", cmd],
                                         "volumes": ["/mnt/disks/oddsky:/mnt/disks/oddsky:rw"]}}],
            "environment": {"variables": {"ODDSKY_UNWISE_PERMISSION": permission}},
            "volumes": [{"gcs": {"remotePath": "oddsky-sky-br3c3-data"}, "mountPath": "/mnt/disks/oddsky"}],
            # measured: 1.9 GB peak per tile-band on a full 2048^2 window; 7 GB leaves room for M31-size tiles
            "computeResource": {"cpuMilli": 2000, "memoryMib": 7168},
            "maxRetryCount": 3, "maxRunDuration": "5400s"}}],
    "allocationPolicy": {
        "instances": [{"policy": {"machineType": "n2d-standard-4", "provisioningModel": "SPOT",
                                  "bootDisk": {"sizeGb": 50}}}],  # 1 GB tile cache + 2-4 GB stacks per task
        "location": {"allowedLocations": ["regions/us-west1"]},
        "serviceAccount": {"email": "oddsky-batch@oddsky-sky-br3c3.iam.gserviceaccount.com"}},
    "logsPolicy": {"destination": "CLOUD_LOGGING"},
    "labels": {"app": "oddsky", "hunt": "h-0012"}}
json.dump(job, open(f"infra/gcp/{name}.json", "w"), indent=1)
print(name, "tasks", tasks, "parallelism", parallelism, "permission", permission)

"""Write a Cloud Batch job spec: N tasks, each processing a slice of a pixel list."""
import json, sys
name, pixel_list, n_pix, per_task, parallelism, run = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
tasks = -(-n_pix // per_task)
cmd = ("set -euo pipefail; PIP_DISABLE_PIP_VERSION_CHECK=1 pip install -q --root-user-action=ignore --no-cache-dir numpy==2.* pandas==2.* pyarrow==21.* && "
       f"python -u /mnt/disks/oddsky/code/neowise_pixel.py --out /mnt/disks/oddsky/runs/{run} "
       f"--pixel-list /mnt/disks/oddsky/code/{pixel_list} --pixels-per-task {per_task}")
job = {
  "taskGroups": [{
    "taskCount": tasks, "parallelism": parallelism,
    "taskSpec": {
      "runnables": [{"container": {"imageUri": "python:3.12-slim", "entrypoint": "/bin/bash", "commands": ["-c", cmd],
                                   "volumes": ["/mnt/disks/oddsky:/mnt/disks/oddsky:rw"]}}],
      "volumes": [{"gcs": {"remotePath": "oddsky-sky-br3c3-data"}, "mountPath": "/mnt/disks/oddsky"}],
      "computeResource": {"cpuMilli": 2000, "memoryMib": 7168},
      "maxRetryCount": 3, "maxRunDuration": "7200s"}}],
  "allocationPolicy": {
    "instances": [{"policy": {"machineType": "n2d-standard-4", "provisioningModel": "SPOT",
                              "bootDisk": {"sizeGb": 30}}}],
    "location": {"allowedLocations": ["regions/us-west1"]},
    "serviceAccount": {"email": "oddsky-batch@oddsky-sky-br3c3.iam.gserviceaccount.com"}},
  "logsPolicy": {"destination": "CLOUD_LOGGING"},
  "labels": {"app": "oddsky", "hunt": "h-0002"}}
json.dump(job, open(f"infra/gcp/{name}.json", "w"), indent=1)
print(name, "tasks", tasks, "parallelism", parallelism)

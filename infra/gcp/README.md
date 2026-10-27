# Sky passes on Google Cloud

Oddsky's survey-scale passes (first: hunt H-0002, infrared afterglows) run as Google Cloud Batch jobs
that read IRSA's NEOWISE Parquet straight from AWS (anonymous, us-west-2; transfer costs us nothing)
and write per-star results to a private GCS bucket.

| | |
|---|---|
| project | `oddsky-sky-br3c3` (billing: nightcap-cloud-billing; budget alert $150 at 25/50/90/100%) |
| region | `us-west1` (Oregon, nearest to the AWS data) |
| bucket | `gs://oddsky-sky-br3c3-data` (private, uniform access) |
| service account | `oddsky-batch@oddsky-sky-br3c3.iam.gserviceaccount.com`: batch.agentReporter, logging.logWriter, objectAdmin on the bucket only |
| workers | `n2d-standard-4` spot VMs, 2 tasks per VM, `python:3.12-slim` + numpy/pandas/pyarrow, bucket mounted at `/mnt/disks/oddsky` |
| code | `src/oddsky/sky/neowise_pixel.py`, copied to `gs://.../code/` |

## Measured (pilots, 2026-10-27)

- 0.30 GB of the needed 23 columns per high-latitude pixel (of ~3.8 GB of Parquet); ~3.1 TB for |b| >= 10 deg.
- 13-30 s to read a pixel (12 yearly files read concurrently), 2-17 s to compute.
- Calibration: ASASSN-21qj (pixel 9840) is flagged blind: W2 +0.79 mag at 79 sigma, W1-W2 redder by 0.39.
- Determinism: re-running pixel 9840 with the concurrent reader gives identical per-star features.

## Run

```bash
gcloud storage cp src/oddsky/sky/neowise_pixel.py infra/gcp/pixels_sky1.txt gs://oddsky-sky-br3c3-data/code/ --project=oddsky-sky-br3c3
python3 infra/gcp/make_job.py sky1 pixels_sky1.txt 10145 20 48 sky1
gcloud batch jobs submit oddsky-sky1 --project=oddsky-sky-br3c3 --location=us-west1 --config=infra/gcp/sky1.json
```

Tasks are idempotent (a pixel with a report is skipped), so a preempted or failed job can simply be resubmitted.
Outputs: `runs/<run>/{features,lightcurves,candidates,reports}/pixel=N.parquet|json`.

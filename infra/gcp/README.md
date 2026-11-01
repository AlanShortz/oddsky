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

## H-0012: mid-IR difference imaging of nearby galaxies (design; not run)

`imaging_tile.py` (the task) and `make_imaging_job.py` (the spec) run `oddsky.imaging` over the unWISE tiles that
the star-forming galaxies within 10 Mpc need. The target list comes from `hunts/H-0012/scripts/targets.py`: 316
galaxies from the UNGC on 332 primary tiles (`hunts/H-0012/work/tiles_h0012.txt`). The LMC and SMC (74 and 30
tiles) are separate projects. The design spec is `h0012a.json`.

| | |
|---|---|
| unit | one task = 2 tiles. Per tile: fetch 25 epochs × 2 bands × (img, invvar, n) = 1.0 GB to the boot disk (≤ 2 connections), run every target galaxy that needs it, write candidates, light curves, detections and 41×41 cutouts to `runs/h0012/<tile>/<galaxy>/`, delete the 1 GB difference stacks |
| measured cost (laptop) | 30-130 s CPU and ≤ 2.5 GB peak per full tile-band; M31's 5 tiles take 15 min with the stacked channel and leave-one-out references |
| estimate | 332 tiles × (~2 min download + ~3 min CPU) ≈ 28 task-hours ≈ 14 VM-hours of `n2d-standard-4` spot ≈ $1-2; wall ~1-2 h at parallelism 25 |
| storage | inputs are never stored in GCS; outputs are ~1-5 MB per galaxy-tile |
| idempotent | a tile with `report.json` is skipped, so resubmit after preemption |

**Hard gate.** The epochal coadds are in A. Meisner's personal NERSC web space, with no release or licence. The spec
is written with `ODDSKY_UNWISE_PERMISSION=NOT-YET`, and the task exits (status 3) before any download until a human
sets it to `granted`. That happens only after Meisner has agreed, or after the data have been mirrored with
permission.

The official fallback is to rebuild the epochs from IRSA L1b frames (`s3://nasa-irsa-wise/`) with `unwise-coadds
--epoch` (GPL-2.0). It needs about 100× the input, plus astrometry.net and the frame indexes, and is best run in
us-east-1 next to the bucket.

```bash
# only after permission; edit the spec to ODDSKY_UNWISE_PERMISSION=granted first
gcloud storage cp -r src infra hunts/H-0012/work/targets_10mpc.csv hunts/H-0012/work/tiles_h0012.txt gs://oddsky-sky-br3c3-data/code/h0012/ --project=oddsky-sky-br3c3
python3 infra/gcp/make_imaging_job.py h0012a h0012/tiles_h0012.txt 332 2 25 $(git rev-parse --short HEAD)
gcloud batch jobs submit oddsky-h0012a --project=oddsky-sky-br3c3 --location=us-west1 --config=infra/gcp/h0012a.json
```

import sys, time, json
from pathlib import Path
from oddsky.data import atlas
ra, dec, out = float(sys.argv[1]), float(sys.argv[2]), Path(sys.argv[3])
url = atlas.submit(ra, dec, mjd_min=57000)
print("task", url, flush=True)
res = atlas.wait(url, poll_s=30, max_wait_s=6 * 3600)
out.write_text(atlas.download(res))
print("saved", out, flush=True)

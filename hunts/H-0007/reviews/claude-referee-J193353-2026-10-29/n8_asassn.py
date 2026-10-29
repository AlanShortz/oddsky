"""Referee J193353: ASAS-SN Sky Patrol v2 cone search + light curve; saves /tmp/j1933nov/asassn.csv.
uv run --with skypatrol python .../n8_asassn.py"""
import sys
import pandas as pd
from pyasassn.client import SkyPatrolClient

RA, DEC = 293.471115, -21.3037472


def main():
    client = SkyPatrolClient()
    print("client OK")
    cat = client.cone_search(ra_deg=RA, dec_deg=DEC, radius=20 / 3600, catalog="master_list")
    print(cat.to_string() if len(cat) else "no catalog match")
    if not len(cat):
        return
    lcs = client.cone_search(ra_deg=RA, dec_deg=DEC, radius=6 / 3600, catalog="master_list", download=True, threads=1)
    df = lcs.data if hasattr(lcs, "data") else lcs
    df.to_csv("/tmp/j1933nov/asassn.csv", index=False)
    print(df.columns.tolist(), len(df))


if __name__ == "__main__":
    main()

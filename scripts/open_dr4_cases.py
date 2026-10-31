"""Open cases for the six events with Gaia DR4 predictions (hunts/H-0009/predictions/): two ATLAS-reproduced H-0008 candidates
and four strong H-0009 events that only NEOWISE saw. Gaia, Gaia epoch photometry (empty until DR4) and NEOWISE come from the
archives; the two ATLAS light curves reuse the hunt's downloads (no chi_n cut: it removes peaks).

    uv run python scripts/open_dr4_cases.py
"""

from __future__ import annotations

from pathlib import Path

from oddsky import skeptic
from oddsky.data import atlas
from oddsky.data.provenance import Provenance
from oddsky.fetch import fetch, open_case

TARGETS = {
    "J163539": dict(gaia="6020322385418675200", ra=248.915374, dec=-35.86921, hunt="H-0008", task="5273734",
                    title="A star in Scorpius brightened ninefold in August 2017 and Gaia never alerted: a microlensing candidate",
                    hook="Found blind in Oddsky hunt H-0008 (NEOWISE x8 in W1 and W2 on 2017 Aug 17). ATLAS shows one smooth, "
                    "achromatic event peaking in mid-August 2017; a point lens with annual parallax fits. Gaia scanned it during the "
                    "event without an alert; DR4 will show what it saw."),
    "J173150": dict(gaia="5952322268527918208", ra=262.961311, dec=-44.763659, hunt="H-0008", task="5273739",
                    title="A G = 15 star in Scorpius brightened nearly eightfold for months in 2018: a long microlensing candidate",
                    hook="Found blind in Oddsky hunt H-0008 (NEOWISE: x1.4 on 2018 Mar 16 and x3.0 on 2018 Aug 27, equal in W1 and W2). ATLAS shows a smooth x7.7 event "
                    "peaking 2018 Jul 11-14; a lens fits only with annual parallax, and the timescale is poorly constrained."),
    "J124517": dict(gaia="5862971688685406976", ra=191.322207, dec=-63.02375, hunt="H-0009", task=None,
                    title="A star in Crux was seven times brighter on one NEOWISE visit in 2018: a test for Gaia DR4",
                    hook="Found blind in Oddsky hunts H-0008/H-0009: x6.9 in both W1 and W2 on 2018 Jul 14, every other visit quiet. "
                    "No optical survey covered it; Gaia DR4 is the second instrument."),
    "J160706": dict(gaia="5932843350525331968", ra=241.778721, dec=-53.624783, hunt="H-0009", task=None,
                    title="A star in Norma brightened eightfold over two NEOWISE visits in 2017: a test for Gaia DR4",
                    hook="Found blind in Oddsky hunt H-0009: x1.8 on 2017 Mar 1, x8.3 on 2017 Aug 15, in both W1 and W2, quiet before "
                    "and after. No optical survey covered it; Gaia DR4 is the second instrument."),
    "J131026": dict(gaia="5863586423081438848", ra=197.610553, dec=-61.383156, hunt="H-0009", task=None,
                    title="A star in Centaurus was 2.5 times brighter on one NEOWISE visit in 2015: a test for Gaia DR4",
                    hook="Found blind in Oddsky hunts H-0008/H-0009: x2.5 in both W1 and W2 on 2015 Aug 1, every other visit quiet. "
                    "No optical survey covered it; Gaia DR4 is the second instrument."),
    "J154239": dict(gaia="5882495205642608896", ra=235.664651, dec=-57.43371, hunt="H-0009", task=None,
                    title="A star in Norma was 2.3 times brighter on one NEOWISE visit in 2017: a test for Gaia DR4",
                    hook="Found blind in Oddsky hunts H-0008/H-0009: x2.3 in both W1 and W2 on 2017 Aug 12, every other visit quiet. "
                    "No optical survey covered it; Gaia DR4 is the second instrument."),
}


def main() -> None:
    for key, t in TARGETS.items():
        store = open_case(f"Gaia DR3 {t['gaia']}", title=t["title"], hook=t["hook"], ra=t["ra"], dec=t["dec"], hunt=t["hunt"])
        print(key, store.path.name, flush=True)
        print(fetch(store, ["gaia", "gaia_epoch", "neowise", "neowise_exp"]), flush=True)
        if t["task"]:
            txt = Path(f"hunts/H-0008/work/atlas/atlas_{key}.txt")
            raw = atlas.parse(txt.read_text())
            df = atlas.to_series(raw, chi_max=1e9)
            store.write_series("atlas", df)
            prov = store.provenance()
            p = Provenance(archive="ATLAS forced photometry (fallingstar-data.com), reduced images",
                           query={"ra": t["ra"], "dec": t["dec"], "use_reduced": True, "task": t["task"]})
            p.rows_raw, p.rows_kept = len(raw), int((df.flag == "").sum())
            p.notes += [f"reused the hunt's server response {txt}", "chi_n cut disabled: chi_n rises with flux"]
            prov["atlas"] = p.model_dump()
            store.write_provenance(prov)
        print(skeptic.run(store)["summary"], flush=True)


if __name__ == "__main__":
    main()

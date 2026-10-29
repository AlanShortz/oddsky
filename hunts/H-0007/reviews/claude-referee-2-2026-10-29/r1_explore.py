"""Referee 2, step 1: per-unit baselines, season-start systematics, chi_n vs flux, airmass. Outside Oddsky tools (pandas)."""
import sys, numpy as np, pandas as pd
from oddsky.data import atlas
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 400)
RA, DEC = 60.1073758, 32.5909576
r = atlas.parse(open(sys.argv[1]).read())
r["unit"] = r.obs.str[:3]
r = r[r.F.isin(["c", "o"]) & (r.dujy > 0) & (r.dujy < 1000) & (r.ujy > 0)].copy()
sites = {"01a": EarthLocation.from_geodetic(-156.2569 * u.deg, 20.7083 * u.deg, 3055 * u.m),
         "02a": EarthLocation.from_geodetic(-155.5763 * u.deg, 19.5362 * u.deg, 3397 * u.m),
         "03a": EarthLocation.from_geodetic(20.8105 * u.deg, -32.3799 * u.deg, 1768 * u.m),
         "04a": EarthLocation.from_geodetic(-70.7313 * u.deg, -30.4710 * u.deg, 2207 * u.m)}
c = SkyCoord(RA * u.deg, DEC * u.deg)
r["airmass"] = np.nan
for un, loc in sites.items():
    m = r.unit == un
    if m.any():
        aa = c.transform_to(AltAz(obstime=Time(r.mjd[m].values, format="mjd"), location=loc))
        r.loc[m, "airmass"] = aa.secz.value
r["event"] = (r.mjd > 57940) & (r.mjd < 58090)
r["season"] = np.floor((r.mjd - 57204) / 365.25).astype(int) + 2015  # season starts ~Jul 1
base = r[~r.event & (r.err == 0)]
print("== baseline flux per unit/band (median uJy, robust sigma %, n) ==")
for (F, un), g in base.groupby(["F", "unit"]):
    med = g.ujy.median(); s = 1.4826 * np.median(np.abs(g.ujy - med)) / med * 100
    print(f"{F} {un}: {med:8.0f}  sig {s:5.2f}%  n {len(g)}  median maj {g.maj.median():.2f}")
# per-season, per-unit baseline (did zero points drift?)
r["season"] = np.floor((r.mjd - 57204) / 365.25).astype(int) + 2015  # season starts ~Jul 1
print("\n== per-season baseline o-band ratio 01a/02a ==")
for s, g in base[base.F == "o"].groupby("season"):
    a = g[g.unit == "01a"].ujy.median(); b = g[g.unit == "02a"].ujy.median()
    print(s, f"01a {a:.0f} ({(g.unit=='01a').sum()})  02a {b:.0f} ({(g.unit=='02a').sum()})  ratio {a/b:.3f}")
# season-start test: flux/baseline vs day-of-season for non-event seasons, o band
ob = base[base.F == "o"].copy()
medo = ob.ujy.median()
ob["fr"] = ob.ujy / medo
ob["doy"] = (Time(ob.mjd.values, format="mjd").datetime64.astype("datetime64[D]") - Time(ob.mjd.values, format="mjd").datetime64.astype("datetime64[Y]")).astype(int)
print("\n== o-band baseline flux ratio by calendar window (all non-event years), nightly medians ==")
ob["night"] = np.floor(ob.mjd - 0.3)
nn = ob.groupby(["night"]).agg(fr=("fr", "median"), doy=("doy", "first"), am=("airmass", "median"), unit=("unit", "first"), chi=("chi_n", "median")).reset_index()
for lo, hi in [(180, 205), (205, 220), (220, 235), (235, 250), (250, 280), (280, 320), (320, 366), (0, 60), (60, 100)]:
    g = nn[(nn.doy >= lo) & (nn.doy < hi)]
    if len(g):
        print(f"doy {lo:3d}-{hi:3d}: n {len(g):3d}  median {g.fr.median():.3f}  mean {g.fr.mean():.3f}  sd {g.fr.std():.3f}  airmass {g.am.median():.2f}")
print("\nearliest nights of each season (o):")
for s, g in nn.assign(season=np.floor((nn.night - 57204) / 365.25).astype(int) + 2015).groupby("season"):
    print(s, g.sort_values("night").head(4)[["night", "doy", "fr", "am", "unit", "chi"]].round(3).values.tolist())
print("\n== event epochs with airmass ==")
print(r[r.event][["mjd", "F", "unit", "m", "ujy", "dujy", "chi_n", "maj", "airmass", "err", "mag5sig"]].round(3).to_string())
# chi_n vs flux in the event: does chi_n scale with flux^2 (PSF mismatch) or blow up (saturation)?
ev = r[r.event & (r.F == "o")]
print("\n== chi_n / (flux/baseline)^2, per unit ==")
for un, g in ev.groupby("unit"):
    print(un, np.c_[g.mjd.round(1), (g.ujy / medo).round(2), g.chi_n.round(0), (g.chi_n / (g.ujy / medo) ** 2).round(0), g.maj.round(2)].tolist())
bb = base[base.F == "o"]
print("baseline chi_n median per unit:", bb.groupby("unit").chi_n.median().round(1).to_dict(), " p90:", bb.groupby("unit").chi_n.quantile(0.9).round(1).to_dict())

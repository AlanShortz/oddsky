"""H-0017: one table of the cooled sources with every test side by side: the Librarian's verdict, the fade between the
2010-11 AllWISE visits (control-corrected), the shift between the AllWISE and CatWISE positions, and the SDSS class.
usage (repo root): candidates.py   -> hunts/H-0017/work/candidates.csv"""
import numpy as np
import pandas as pd

W = "hunts/H-0017/work/"
ids = pd.read_csv(W + "cooled_id.csv")
ids = ids[~ids.star][["designation", "ra", "dec", "sigra", "sigdec", "w1mpro_allwise", "w2mpro_allwise", "d1", "d2", "dcolor", "ext_flg"]]
lib = pd.read_csv(W + "librarian_109.csv")[["designation", "verdict", "complete", "simbad", "simbad_otype", "ned", "ned_type", "z", "n_papers",
                                             "n_topical", "newest_topical", "newest_title", "shelves", "catalogues"]]
ep = pd.read_csv(W + "epochs_2010.csv")[["designation", "n_ep", "dt_days", "dw2_2010", "dw1_2010"]]
ctl = pd.read_csv(W + "epochs_2010_control.csv")
ctl = ctl[ctl.n_ep >= 2]
cw = pd.read_csv(W + "catwise_109.csv")[["designation", "status", "n_catwise", "cw_sep", "dra", "ddec", "cw_sigra", "cw_sigdec", "cw_nb"]]
sd = pd.read_csv(W + "sdss_spectra.csv")
sd = sd[sd.n_spec > 0].sort_values("mjd").drop_duplicates("designation")[["designation", "spec_class", "subclass", "mjd"]]
x = ids.merge(lib, on="designation").merge(ep, on="designation").merge(cw, on="designation").merge(sd, on="designation", how="left")
assert len(x) == 96 and x.complete.all() and (x.status == "ok").all()
x["fade_2010"] = x.dw2_2010 - ctl.dw2_2010.median()  # W2, last minus first AllWISE visit, control offset removed
x["shift_sigma"] = np.hypot(x.dra / np.hypot(x.sigra, x.cw_sigra), x.ddec / np.hypot(x.sigdec, x.cw_sigdec))
x["known"] = x.verdict == "studied"
x["declining"] = x.fade_2010 > 0.15
# The position test does not discriminate: 22 of 131 unchanged control galaxies shift by more than 1 arcsec between AllWISE
# and CatWISE (deblending), against 11 of these 96. Only a shift beyond anything in the control is flagged.
kc = pd.read_csv(W + "catwise_control.csv")
x["moved"] = x.cw_sep > kc.cw_sep.max()
x["klass"] = np.select([x.known, x.declining], ["already studied or a catalogued variable", "declining in 2010, no transient literature found"],
                       "no change seen within 2010")
cols = ["designation", "klass", "ra", "dec", "z", "ned_type", "simbad", "simbad_otype", "w2mpro_allwise", "d2", "dcolor", "fade_2010", "n_ep",
        "cw_sep", "moved", "n_catwise", "ext_flg", "spec_class", "subclass", "verdict", "n_papers", "n_topical", "newest_topical", "shelves", "catalogues"]
x.sort_values(["klass", "fade_2010"], ascending=[True, False])[cols].round(4).to_csv(W + "candidates.csv", index=False)
print(x.klass.value_counts().to_string())
print("control: shifts > 1 arcsec in", int((kc.cw_sep > 1).sum()), "of", len(kc), "; maximum", round(kc.cw_sep.max(), 2), "| here > 1 arcsec:",
      int((x.cw_sep > 1).sum()), "of", len(x), "; beyond the control maximum:", x[x.moved].designation.tolist())
p = x[x.klass == "declining in 2010, no transient literature found"].sort_values("fade_2010", ascending=False)
print(p[["designation", "z", "ned_type", "w2mpro_allwise", "d2", "fade_2010", "cw_sep", "spec_class", "subclass", "n_papers"]].head(8).round(2).to_string())

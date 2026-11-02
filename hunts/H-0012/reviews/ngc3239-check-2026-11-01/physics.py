"""Blackbody temperatures, luminosities and radii of the WISE transient light (2020-11-23, 2021-04-28, 2021-11-22),
the HST 2021 optical point source and the JWST 2024 dust source, at 7.9 Mpc (UNGC TF) and 10.1 Mpc (SN 2012A SN II).
Also the extinction implied by the HST colour vs. by the brightness for a normal SN, and radiated IR energy."""
import json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
h, c, k, sb, Lsun, pc = 6.626e-34, 2.998e8, 1.381e-23, 5.670e-8, 3.828e26, 3.0857e16
lc = {int(r["epoch"]): r for r in json.load(open(HERE / "wise_result.json"))["colour"]}
J = json.load(open(HERE / "spitzer_check.json"))["jwst_bb"]
H = json.load(open(HERE / "hst_diff.json"))["phot"]
LW = {1: 3.368, 2: 4.618}  # WISE isophotal wavelengths (um)

def bnu(l, T):
    nu = c / (l * 1e-6); return nu ** 3 / np.expm1(h * nu / (k * T))

def bbfit(f1, f2, l1, l2):
    Ts = np.linspace(200, 5000, 48001)
    T = Ts[np.argmin(np.abs(bnu(l2, Ts) / bnu(l1, Ts) - f2 / f1))]
    nu = c / (l1 * 1e-6); x = h * nu / (k * T)
    frac = 15 / np.pi ** 4 * x ** 4 / np.expm1(x)
    Fbol = nu * f1 * 1e-32 / frac
    return float(T), Fbol

out = {}
for D in (7.9, 10.1):
    d = D * 1e6 * pc; mu = 5 * np.log10(D * 1e5)
    o = dict(mu=mu)
    for ep, r in lc.items():
        T, Fbol = bbfit(r["W1_uJy"], r["W2_uJy"], LW[1], LW[2])
        L = Fbol * 4 * np.pi * d ** 2 / Lsun
        R = np.sqrt(L * Lsun / (4 * np.pi * sb * T ** 4))
        nuLnu1 = c / (LW[1] * 1e-6) * r["W1_uJy"] * 1e-32 * 4 * np.pi * d ** 2 / Lsun
        o[f"WISE_ep{ep}"] = dict(mjd=r["mjd"], T_K=T, Lbol_Lsun=float(L), R_au=float(R / 1.496e11), R_cm=float(R * 100),
                                 nuLnu_W1_Lsun=float(nuLnu1), M_W1_vega=r["W1_vega"] - mu, M_W2_vega=r["W2_vega"] - mu, W1mW2=r["W1mW2"])
    f6 = H["DIFF F606W21-ACSF606W22"]["flux_uJy"]; f8 = H["DIFF F814W21-F814W25"]["flux_uJy"]
    m6, m8 = 23.9 - 2.5 * np.log10(f6), 23.9 - 2.5 * np.log10(f8)
    # Vega: WFC3/UVIS AB-Vega offsets F606W +0.10, F814W +0.42 (approx.)
    o["HST_2021"] = dict(F606W_AB=m6, F814W_AB=m8, colour_AB=m6 - m8, colour_vega=(m6 - 0.10) - (m8 - 0.42),
                         M_F606W_AB=m6 - mu, M_F814W_AB=m8 - mu,
                         nuLnu_opt_Lsun=float((c / 5.9e-7 * f6 + c / 8.0e-7 * f8) * 1e-32 * 4 * np.pi * d ** 2 / Lsun / 2))
    # W1 interpolated to the HST epoch (exponential between ep15 and ep16)
    t15, t16 = lc[15]["mjd"], lc[16]["mjd"]
    tau = (t16 - t15) / np.log(lc[15]["W1_uJy"] / lc[16]["W1_uJy"])
    w1_hst = lc[15]["W1_uJy"] * np.exp(-(59261.8 - t15) / tau)
    o["HST_2021"]["W1_at_HST_uJy"] = float(w1_hst); o["HST_2021"]["F606W_minus_W1_AB"] = float(m6 - (23.9 - 2.5 * np.log10(w1_hst)))
    o["HST_2021"]["F814W_minus_W1_AB"] = float(m8 - (23.9 - 2.5 * np.log10(w1_hst)))
    o["W1_decline_tau_days_ep15_16"] = float(tau)
    o["JWST_2024"] = dict(T_K=J["T_K"], Lbol_Lsun=J["Lbol_Lsun_7p9Mpc"] * (D / 7.9) ** 2, R_au=J["R_bb_au"] * D / 7.9)
    # IR energy radiated after first detection: L(t)=L15*exp(-(t-t15)/tau_L) with the observed L15 -> L16 decay
    L15, L16 = o["WISE_ep15"]["Lbol_Lsun"], o["WISE_ep16"]["Lbol_Lsun"]
    tauL = (t16 - t15) / np.log(L15 / L16)
    o["E_IR_after_first_detection_erg"] = float(L15 * Lsun * tauL * 86400 * 1e7)
    out[f"{D}Mpc"] = o
# extinction arithmetic (R_V = 3.1, Cardelli: A_F606W/A_V ~ 0.92, A_F814W/A_V ~ 0.60)
a6, a8 = 0.92, 0.60
col = out["7.9Mpc"]["HST_2021"]["colour_AB"]
ext = {}
for lab, c0, M8 in (("SN IIP plateau (V-I)0~0.6 Vega, M_I~-17", 0.6 - 0.32, -17.0 + 0.42), ("SN IIP nebular tail ~200 d, (V-I)0~1.1, M_I~-13", 1.1 - 0.32, -13.0 + 0.42),
                    ("faint SN IIP tail ~200 d (2005cs-like), M_I~-10.5", 1.1 - 0.32, -10.5 + 0.42), ("ILRT at ~150-250 d, (V-I)0~1.5, M_I~-9 to -11", 1.5 - 0.32, -10.0 + 0.42)):
    Av_colour = (col - c0) / (a6 - a8)
    Av_bright = (out["7.9Mpc"]["HST_2021"]["M_F814W_AB"] - M8) / a8
    ext[lab] = dict(Av_from_colour=float(Av_colour), Av_needed_for_brightness=float(Av_bright))
out["extinction_check_7.9Mpc"] = ext
print(json.dumps(out, indent=1))
json.dump(out, open(HERE / "physics.json", "w"), indent=1)

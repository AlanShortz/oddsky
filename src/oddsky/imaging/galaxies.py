"""Target galaxies: centre, optical extent (D25 ellipse), orientation, distance.

Positions and D25 from RC3/HyperLEDA (via NED); distances are TRGB/Cepheid where available.
`search_scale` enlarges the D25 ellipse for the search region (IR-bright AGB/RSG populations and
transients sit out to and beyond D25 in big spirals)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Galaxy:
    name: str
    ra: float  # deg, nucleus
    dec: float
    d25_arcmin: float  # major-axis diameter
    ba: float  # minor/major axis ratio
    pa_deg: float  # position angle of the major axis, east of north
    dist_mpc: float
    nucleus_mask_arcsec: float = 60.0  # radius masked around the nucleus (PSF-mismatch residuals)
    search_scale: float = 1.2
    extra_masks: tuple = ()  # (ra, dec, radius_arcsec): companion nuclei, very bright clusters

    def ellipse_r(self, ra, dec) -> np.ndarray:
        """Elliptical radius in units of the D25 semi-major axis (1 = on the D25 ellipse)."""
        ra, dec = np.asarray(ra, float), np.asarray(dec, float)
        dx = (((ra - self.ra + 180) % 360) - 180) * np.cos(np.radians(self.dec)) * 60  # arcmin, +east
        dy = (dec - self.dec) * 60
        pa = np.radians(self.pa_deg)
        major = dx * np.sin(pa) + dy * np.cos(pa)
        minor = dx * np.cos(pa) - dy * np.sin(pa)
        a = self.d25_arcmin / 2
        return np.hypot(major / a, minor / (a * self.ba))

    def inside(self, ra, dec, scale: float | None = None) -> np.ndarray:
        return self.ellipse_r(ra, dec) <= (self.search_scale if scale is None else scale)

    def boundary(self, n: int = 360, scale: float | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Points on the (scaled) D25 ellipse, for tile selection."""
        s = self.search_scale if scale is None else scale
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        a = self.d25_arcmin / 2 * s / 60
        b = a * self.ba
        major, minor = a * np.cos(t), b * np.sin(t)
        pa = np.radians(self.pa_deg)
        dx = major * np.sin(pa) + minor * np.cos(pa)
        dy = major * np.cos(pa) - minor * np.sin(pa)
        return self.ra + dx / np.cos(np.radians(self.dec)), self.dec + dy

    def grid(self, step_deg: float = 0.1, scale: float | None = None):
        """Points filling the (scaled) ellipse; with `boundary`, enough to find every tile."""
        s = self.search_scale if scale is None else scale
        a = self.d25_arcmin / 2 * s / 60
        g = np.arange(-a, a + step_deg, step_deg)
        dx, dy = np.meshgrid(g, g)
        ra = self.ra + dx.ravel() / np.cos(np.radians(self.dec))
        dec = self.dec + dy.ravel()
        keep = self.inside(ra, dec, s)
        return ra[keep], dec[keep]


GALAXIES = {
    g.name: g
    for g in [
        # De et al. 2024 adopt 770 kpc for M31
        Galaxy("M31", 10.684708, 41.268750, 190.5, 0.32, 38.0, 0.77, nucleus_mask_arcsec=150.0,
               extra_masks=((10.674300, 40.865287, 45.0), (10.091847, 41.685308, 30.0))),  # M32, NGC 205
        Galaxy("M33", 23.462042, 30.660222, 70.8, 0.59, 23.0, 0.86, nucleus_mask_arcsec=40.0),
        # NGC 6946: host of N6946-BH1 and SN 2017eaw; 7.72 Mpc TRGB (Anand et al. 2018)
        Galaxy("NGC6946", 308.718015, 60.153915, 11.5, 0.85, 52.0, 7.72, nucleus_mask_arcsec=25.0,
               search_scale=1.5),
        Galaxy("M101", 210.802267, 54.348950, 28.8, 0.93, 39.0, 6.9, nucleus_mask_arcsec=25.0),
        Galaxy("M81", 148.888221, 69.065295, 26.9, 0.52, 157.0, 3.6, nucleus_mask_arcsec=40.0),
        Galaxy("M83", 204.253958, -29.865417, 12.9, 0.89, 45.0, 4.9, nucleus_mask_arcsec=30.0),
        Galaxy("NGC2403", 114.214167, 65.602556, 21.9, 0.56, 127.0, 3.2, nucleus_mask_arcsec=15.0),
        Galaxy("NGC300", 13.722833, -37.684389, 21.9, 0.71, 111.0, 2.0, nucleus_mask_arcsec=10.0),
        Galaxy("M51", 202.469575, 47.195258, 11.2, 0.62, 163.0, 8.6, nucleus_mask_arcsec=25.0,
               search_scale=1.5),
    ]
}

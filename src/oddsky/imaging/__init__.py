"""Mid-infrared difference imaging of nearby galaxies (hunt H-0012).

The method behind M31-2014-DS1 (De et al. 2024, Science 386, 2410.14778): subtract a reference from
every six-monthly WISE/NEOWISE image of a galaxy and look for stars that brighten or vanish.

Data: the unWISE time-resolved ("epochal") coadds (Meisner et al. 2018, 2023), 2048 x 2048 px
tiles at 2.75"/px on the WISE Atlas tile centres, one coadd per tile per ~6-month sky pass,
2010-2024 in the neo11 build. Every epoch of a tile shares the tile's TAN WCS, so the images are
already on a common pixel grid and no resampling is needed.

Modules, in pipeline order:

- `tiles`      unWISE tile table; which tiles cover a galaxy
- `fetch`      download epochal coadds (image, inverse variance, coverage) into a disk cache
- `stack`      load all epochs of a tile/band (optionally a sub-window) as one array + metadata
- `psf`        empirical PSF from isolated stars; PSF evaluation at sub-pixel offsets
- `diff`       reference images (incl. leave-one-out), PSF-matching kernels, difference images
- `detect`     matched-filter S/N maps, peak finding, masks, cross-epoch grouping
               (the stacked NEOWISE-minus-2010 channel lives in pipeline.stack_channel)
- `photometry` forced PSF photometry on difference and direct images (light curves)
- `metrics`    variability metrics and a DS1-like vs long-period-variable classification
- `galaxies`   target galaxies (centre, size, orientation, distance)
- `pipeline`   the end-to-end run over a galaxy: candidates table + light curves
"""

ZP_VEGA = 22.5  # unWISE images are in Vega "nanomaggies": m = 22.5 - 2.5 log10(flux)
PIXSCALE = 2.75  # arcsec / px
# Vega -> AB offsets and Vega zero-point flux densities (Jarrett et al. 2011)
AB_MINUS_VEGA = {1: 2.699, 2: 3.339}
F0_JY = {1: 309.540, 2: 171.787}


def flux_to_mjy(flux, band: int):
    """unWISE image units (Vega nanomaggies) to mJy."""
    return flux * 1e-9 * F0_JY[band] * 1e3


def mjy_to_flux(mjy, band: int):
    return mjy / (1e-9 * F0_JY[band] * 1e3)

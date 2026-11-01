# DRAFT email to Aaron Meisner (not sent; for Alan to review and send)

**To:** Aaron Meisner (NSF NOIRLab)
**Subject:** Using the time-resolved unWISE (neo11) epoch coadds for a nearby-galaxy mid-IR variability search

Dear Dr. Meisner,

I run Oddsky (oddsky.ai), an open project that uses public sky-survey archives to look for unusual stars. We have built a
mid-infrared difference-imaging pipeline on the time-resolved unWISE coadds (the 25 neo11 epochs, 2010-2024) and tested it on M31:
run blind, it recovers M31-2014-DS1 with a light curve matching De et al. (2024), and in NGC 6946 it recovers SN 2017eaw and
measures a WISE light curve of the failed-supernova candidate N6946-BH1 consistent with the published Spitzer fade.

We found the per-epoch coadds in your NERSC directory and want to ask before going further:

1. Are you happy for us to use them, and how would you like them credited (which paper or papers)?
2. We would like to extend the search to the ~300 star-forming galaxies within about 10 Mpc, which needs roughly 400 tiles (on
   the order of 400 GB). Is there a preferred way to obtain that volume (another mirror, a rate limit, a time of day), or would
   you rather we rebuild the epochs ourselves from IRSA's single-exposure frames with unwise_coadd?
3. Are there known calibration differences between the neo builds that we should correct for? We see the documented offset of
   the first WISE sky pass, and the epochs come from several software versions.

Everything we produce is open, and we would be glad to share the candidate lists and code with you first.

With thanks,
Alan Shortz

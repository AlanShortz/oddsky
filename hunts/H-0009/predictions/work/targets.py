"""Targets for the DR4 proposal (H-0009 follow-up). Coordinates are the Gaia DR3 positions (epoch 2016) from sky4_classified."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LC_DIRS = [os.path.expanduser("~/oddsky-runs/h0009/lightcurves"), os.path.expanduser("~/oddsky-runs/h0008/lightcurves")]

T = {
    "J163539": dict(name="J163539.69-355208.3", gaia="6020322385418675200", ra=248.915374, dec=-35.869210, G=18.313,
                    pixel=10694, cntr=2480036401351054461, t_nw=57982.4),
    "J173150": dict(name="J173150.73-444549.3", gaia="5952322268527918208", ra=262.961311, dec=-44.763659, G=15.071,
                    pixel=10573, cntr=2620045501351055125, t_nw=58357.2),
    "J124517": dict(name="J124517.35-630125.0", gaia="5862971688685406976", ra=191.322207, dec=-63.023750, G=17.756,
                    pixel=10414, cntr=1915063701351056199, t_nw=58313.4),
    "J160706": dict(name="J160706.90-533729.5", gaia="5932843350525331968", ra=241.778721, dec=-53.624783, G=18.003,
                    pixel=10538, cntr=2416053101351006664, t_nw=57980.6),
    "J131026": dict(name="J131026.53-612259.2", gaia="5863586423081438848", ra=197.610553, dec=-61.383156, G=17.749,
                    pixel=10415, cntr=1989062101351056660, t_nw=57235.8),
    "J154239": dict(name="J154239.48-572601.4", gaia="5882495205642608896", ra=235.664651, dec=-57.433710, G=17.242,
                    pixel=10449, cntr=2353057601351031167, t_nw=57977.9),
}

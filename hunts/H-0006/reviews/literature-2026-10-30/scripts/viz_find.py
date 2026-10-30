import sys, warnings
warnings.filterwarnings("ignore")
from astroquery.vizier import Vizier
v = Vizier(vizier_server="vizier.idia.ac.za", timeout=120)
for kw in sys.argv[1:]:
    try:
        c = v.find_catalogs(kw, max_catalogs=200)
        print(f"\n## find_catalogs('{kw}') -> {len(c)}")
        for k, m in c.items(): print("  ", k, "|", m.description[:120])
    except Exception as e:
        print(f"\n## find_catalogs('{kw}') -> ERROR {e!r}")

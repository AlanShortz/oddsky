import sys
from astroquery.vizier import Vizier
out=sys.argv[1]; srv=sys.argv[2]
v = Vizier(columns=["**"], row_limit=-1); v.VIZIER_SERVER=srv; v.TIMEOUT=120
tl = v.get_catalogs("J/ApJ/839/88/table1")
t = tl[0]
with open(f"{out}/spirits_kasliwal2017_table1.csv","w") as f:
    f.write("# VizieR J/ApJ/839/88/table1 (SPIRITS galaxy sample)\n"); t.write(f, format='csv')
print("table1 rows:", len(t), "cols:", t.colnames)
names = [" ".join(str(x) for x in r) for r in t]
hits = [n for n in names if "3239" in n.replace(" ","")]
print("rows mentioning 3239:", hits)
import re
ngc = sorted(set(re.findall(r'NGC\s*\d+', " ".join(names))))
print("n NGC names:", len(ngc)); print([n for n in ngc if 3000<int(re.sub(r'\D','',n))<3500])

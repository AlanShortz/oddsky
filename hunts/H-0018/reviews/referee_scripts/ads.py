import os,json,urllib.request,urllib.parse
tok=open(os.path.expanduser('~/.config/oddsky/ads-token')).read().strip()
qs=[
 'full:"astrometric orbits" full:"Gaia" full:("ecliptic" AND ("clockwise" OR "counterclockwise" OR "retrograde" OR "prograde")) year:2022-2026',
 'full:"nss_two_body_orbit" full:("sense of" AND "ecliptic") year:2022-2026',
 'full:("Gaia" AND "astrometric" AND "orbit") full:"same sense as" full:"parallactic" year:2018-2026',
 'full:"parallactic ellipse" full:"orbit" full:("sense" OR "direction") full:"Gaia" year:2020-2026',
 'full:"inclination" full:"Gaia" full:"one year" full:"ecliptic" full:"asymmetr" full:"astrometric binar" year:2022-2026',
 'abs:("astrometric" AND "binaries" AND "inclination distribution" AND "Gaia") year:2022-2026',
 'full:("cos i" AND "Gaia" AND "NSS" AND "ecliptic latitude") year:2022-2026',
 'full:"Thiele-Innes" full:"ecliptic" full:"parallax" full:"degenerate" year:2022-2026',
 'abs:("binary" AND ("angular momentum" OR "orbital plane" OR "orbital pole") AND "Galactic" AND ("alignment" OR "dipole" OR "anisotropy")) year:2021-2026',
 'abs:("wide binaries" AND ("angular momentum" OR "orientation" OR "orbital plane") AND ("Galactic plane" OR "Galactic rotation" OR "alignment")) year:2019-2026',
 'full:"wide binaries" full:"Gaia" full:("prograde" AND "retrograde") full:"Galactic" year:2019-2026',
 'abs:("gaiamock" OR ("Gaia" AND "astrometric" AND "selection function" AND "binaries" AND "orbit")) year:2024-2026',
 'citations(bibcode:2018MNRAS.476.5658B)',
 'abs:("parallax" AND "orbital" AND "bias" AND "NSS" AND "Gaia") year:2022-2026',
 'full:("Gaia" AND "astrometric orbit" AND "parallax error" AND "sense") year:2022-2026',
 'full:"orbital sense" full:"Gaia" year:2020-2026',
 'full:"sense of revolution" full:"Gaia" year:2020-2026',
 'full:"direction of motion" full:"astrometric" full:"parallax" full:"one-year" full:"Gaia DR3" year:2022-2026',
]
seen={}
for q in qs:
    u='https://api.adsabs.harvard.edu/v1/search/query?'+urllib.parse.urlencode({'q':q,'fl':'bibcode,title,year,first_author,citation_count','rows':25,'sort':'date desc'})
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+tok})
    try:
        d=json.load(urllib.request.urlopen(r,timeout=40))['response']
    except Exception as e:
        print('ERR',q,e);continue
    print('\n##',q,'N=',d['numFound'])
    for x in d['docs']:
        print(' ',x['bibcode'],x['first_author'][:18],'|',(x.get('title') or [''])[0][:95])

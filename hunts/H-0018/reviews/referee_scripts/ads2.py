import os,json,urllib.request,urllib.parse
tok=open(os.path.expanduser('~/.config/oddsky/ads-token')).read().strip()
qs=[
 'body:"sense" body:"ecliptic" body:"astrometric orbit" body:"Gaia" year:2022-2026',
 'body:("astrometric" AND "orbits") body:("clockwise" AND "counterclockwise") body:"Gaia DR3" year:2022-2026',
 'body:"same direction as the Earth" body:"Gaia" year:2018-2026',
 'body:"opposite direction" body:"parallactic" body:"astrometric orbit" year:2018-2026',
 'body:"retrograde" body:"parallax" body:"one year" body:"NSS" year:2022-2026',
 'body:"degenerate with parallax" body:"inclination" body:"Gaia" year:2022-2026',
 'body:"parallax" body:"Thiele-Innes" body:"ecliptic latitude" year:2022-2026',
 'body:"gaiamock" body:"ecliptic" year:2024-2026',
 'body:"orbital sense" body:"astrometric" year:2020-2026',
 'body:"signed" body:"cos i" body:"Gaia" body:"astrometric" year:2022-2026',
 'body:"cos i" body:"asymmetry" body:"Gaia" body:"astrometric orbit" year:2022-2026',
 'body:"inclination" body:"asymmetric" body:"i > 90" body:"Gaia" body:"astrometric" year:2022-2026',
 'body:"orbital pole" body:"Gaia" body:"binaries" year:2022-2026',
 'body:"binary" body:"Galactic rotation" body:"orbital angular momentum" body:"aligned" body:"Gaia" year:2020-2026',
 'body:"wide binaries" body:"dipole" body:"angular momentum" year:2019-2026',
 'title:("orbit" AND "orientation" AND "Gaia" AND "binar") year:2020-2026',
 'title:("orbital planes" OR "orbital poles" OR "orbit orientation") year:2020-2026',
 'bibcode:2026arXiv261106915Y',
 'bibcode:2026PhR..1150....1P',
 'abs:"Oort constants" abs:Gaia year:2017-2026',
]
for q in qs:
    u='https://api.adsabs.harvard.edu/v1/search/query?'+urllib.parse.urlencode({'q':q,'fl':'bibcode,title,year,first_author,identifier','rows':12,'sort':'date desc','hl':'true','hl.fl':'body','hl.snippets':2,'hl.fragsize':180})
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+tok})
    try:
        j=json.load(urllib.request.urlopen(r,timeout=40))
    except Exception as e:
        print('ERR',q,e);continue
    d=j['response'];hl=j.get('highlighting',{})
    print('\n##',q,'N=',d['numFound'])
    for x in d['docs']:
        print(' ',x['bibcode'],x['first_author'][:18],'|',(x.get('title') or [''])[0][:90])

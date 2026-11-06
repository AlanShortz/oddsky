import os,json,urllib.request,urllib.parse,re
tok=open(os.path.expanduser('~/.config/oddsky/ads-token')).read().strip()
def go(q,hl='body',n=4,rows=8,frag=220):
    u='https://api.adsabs.harvard.edu/v1/search/query?'+urllib.parse.urlencode({'q':q,'fl':'bibcode,title,first_author','rows':rows,'sort':'date desc','hl':'true','hl.fl':hl,'hl.snippets':n,'hl.fragsize':frag})
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+tok});j=json.load(urllib.request.urlopen(r,timeout=40))
    h=j.get('highlighting',{});print('\n##',q,'N=',j['response']['numFound'])
    for d in j['response']['docs']:
        print(' *',d['bibcode'],d['first_author'][:16],(d.get('title')or[''])[0][:70])
        for s in (h.get(d['id']) or h.get(d.get('bibcode')) or {}).get('body',[]):
            print('     ',re.sub(r'\s+',' ',s)[:260])
go('body:"ecliptic" body:"cos i" body:"astrometric" (bibcode:2023A&A...674A..34G OR bibcode:2024OJAp....7E.100E OR bibcode:2025ApJ...987..215L OR bibcode:2026AJ....171...18L OR bibcode:2026PhR..1150....1P OR bibcode:2026arXiv260935999Y OR bibcode:2026arXiv260909631W)',n=5)
go('(body:"parallactic motion" OR body:"parallax motion") body:"orbital motion" body:"sense" body:"Gaia" year:2023-2026',n=3,rows=12)
go('body:"prograde" body:"parallactic" body:"astrometric" body:"Gaia" year:2020-2026',n=2,rows=10)
go('body:"inclination" body:"ecliptic latitude" body:"astrometric orbit" year:2022-2026',n=2,rows=12)
go('body:"hemisphere" body:"astrometric orbits" body:"Gaia" body:"inclination" year:2022-2026',n=2,rows=10)
go('body:"parallax" body:"anticorrelated" body:"one-year period" body:"astrometric" body:"Gaia" year:2023-2026',n=2,rows=6)
go('body:"two-year" body:"parallax" body:"astrometric orbit" body:"Gaia" year:2022-2026',n=2,rows=10)
go('body:"2 yr" body:"parallax" body:"harmonic" body:"astrometric" body:"Gaia" year:2022-2026',n=2,rows=8)
go('title:"Oort constants" year:2017-2026',n=1,rows=6)
go('bibcode:2017MNRAS.468L..63B',n=1,rows=1)

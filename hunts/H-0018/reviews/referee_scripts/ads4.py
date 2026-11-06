import os,json,urllib.request,urllib.parse
tok=open(os.path.expanduser('~/.config/oddsky/ads-token')).read().strip()
for q in ['bibcode:2017MNRAS.468L..63B','title:"Oort constants" abs:"Gaia DR2"','title:"Oort constants" abs:"Gaia EDR3"','author:"Makarov, V" title:"face-on"']:
    u='https://api.adsabs.harvard.edu/v1/search/query?'+urllib.parse.urlencode({'q':q,'fl':'bibcode,title,abstract,first_author,year','rows':3})
    r=urllib.request.Request(u,headers={'Authorization':'Bearer '+tok})
    for d in json.load(urllib.request.urlopen(r,timeout=40))['response']['docs']:
        print(d['bibcode'],d['first_author'],d['title'][0][:80]);print('   ',d.get('abstract','')[:700])

"""The Librarian: is it new? Offline: the services are replaced by what they returned on 2026-11-05 for
RA 216.0069, Dec 29.8412, the galaxy H-0017 called its "best candidate" (object 12 of Wang et al. 2018)."""
import math

import pytest

from oddsky import librarian, skeptic
from oddsky.data.provenance import Provenance
from oddsky.librarian import load_shelves, matched_topics, prior_art, shelf_hits

RA, DEC = 216.0069, 29.8412
WANG = "2018MNRAS.477.2943W"
SIMBAD_OBJ = {"main_id": "2MASX J14240163+2950285", "otype": "EmG", "ra": 216.00692860053996, "dec": 29.84119873223,
              "sep_arcsec": 0.09, "n_refs": 5}
# n_objects is SIMBAD's ref.nbobject: the number of objects each paper lists
SIMBAD_PAPERS = [
    {"bibcode": "2023PASP..135c4101G", "n_objects": 147,
     "title": "A Census of Archival X-Ray Spectra for Modeling Tidal Disruption Events."},
    {"bibcode": "2005AJ....130..496J", "n_objects": 315,
     "title": "Spectroscopy of KISS emission-line galaxy candidates. III. A second set of MDM observations."},
    {"bibcode": "2001AJ....121...66S", "n_objects": 1316,
     "title": "The KPNO International Spectroscopic Survey. II. H{alpha}-selected survey list 1."},
    {"bibcode": "2014ApJ...788...45T", "n_objects": 224173,
     "title": "Luminosity and redshift dependence of the covering factor of active "
              "galactic nuclei viewed with WISE and Sloan Digital Sky Survey."},
    {"bibcode": WANG, "n_objects": 23,
     "title": "Long-term decline of the mid-infrared emission of normal galaxies: dust echo of tidal disruption flare?"},
]
NED_OBJ = {"prefname": "WISEA J142401.66+295028.4", "type": "G", "z": 0.085530415, "z_bibcode": None, "ra": 216.0069291,
           "dec": 29.8412329, "sep_arcsec": 0.03}
ADS_PAPERS = [
    {"bibcode": WANG, "year": "2018",
     "title": "Long-term decline of the mid-infrared emission of normal galaxies: dust echo of tidal disruption flare?"},
    {"bibcode": "2001AJ....121...66S", "year": "2001",
     "title": "The KPNO International Spectroscopic Survey. II. Hα-selected Survey List 1"},
    {"bibcode": "2005AJ....130..496J", "year": "2005",
     "title": "Spectroscopy of KISS Emission-Line Galaxy Candidates. III. A Second Set of MDM Observations"},
]
QUIET = [p for p in SIMBAD_PAPERS if p["bibcode"] in ("2005AJ....130..496J", "2001AJ....121...66S", "2014ApJ...788...45T")]


def ok(**kw):
    return Provenance(archive="fake", **kw)


def sim(papers=None, **obj):
    """What simbad() returns for one object within the radius (the H-0017 galaxy unless fields are given)."""
    o = {**SIMBAD_OBJ, **obj}
    return ({"object": o, "nearest": o, "n_objects": 1, "objects": [o], "nearby": None,
             "papers": [dict(p) for p in (SIMBAD_PAPERS if papers is None else papers)]}, ok())


def ned_is(*objs, nearby=None, **prov):
    """What ned() returns for these objects within the radius, nearest first."""
    objs = [dict(o) for o in objs]
    return ({"object": {**objs[0], "n_objects": len(objs)} if objs else None, "objects": objs, "nearby": nearby},
            ok(**({"status": "empty"} if not objs and not prov else prov)))


def cats(**given):
    """What catalogues() returns: every catalogue empty, except `key=[hit, ...]` (a hit) or `key="unavailable"`."""
    out = []
    for c in librarian.CATALOGUES:
        g = given.get(c["key"], [])
        down = g == "unavailable"
        out.append({"key": c["key"], "name": c["name"], "kind": c["kind"], "bibcode": c["bibcode"],
                    "status": "unavailable" if down else "ok" if g else "empty", "notes": ["timeout"] if down else [],
                    "hits": [] if down else [dict(h) for h in g]})
    assert not set(given) - {c["key"] for c in librarian.CATALOGUES}
    return out


def patch(monkeypatch, tmp_path, simbad=None, ned=None, ads=None, catalogues=None):
    """Replace the services (and point the shelves at an empty directory). Each argument is what the service function
    returns; the default is the real answer for the H-0017 galaxy, which is in none of the catalogues. Returns the list
    of calls: `asked` gets (names, bibcodes) put to ADS, and `asked.epochs` the epoch each SIMBAD lookup was given."""
    simbad = simbad or sim()
    ned = ned or ned_is(NED_OBJ)
    ads = ads or ([dict(p) for p in ADS_PAPERS], ok())
    catalogues = cats() if catalogues is None else catalogues

    class Asked(list):
        epochs: list

    asked = Asked()
    asked.epochs = []
    monkeypatch.setattr(librarian, "simbad", lambda ra, dec, radius_arcsec=5.0, epoch=None: (asked.epochs.append(epoch), simbad)[1])
    monkeypatch.setattr(librarian, "ned", lambda ra, dec, radius_arcsec=5.0: ned)
    monkeypatch.setattr(librarian, "ads_papers", lambda names, bibcodes=(): (asked.append((list(names), list(bibcodes))), ads)[1])
    monkeypatch.setattr(librarian, "catalogues", lambda ra, dec, radius_arcsec=5.0: catalogues)
    monkeypatch.setattr(librarian, "SHELVES_DIR", tmp_path / "no-shelves")
    return asked


NO_SIMBAD = ({"object": None, "nearest": None, "n_objects": 0, "objects": [], "papers": [], "nearby": None}, ok(status="empty"))
NO_NED = ned_is()
NED_DOWN = ned_is(status="unavailable", notes=["timeout"])


# ----------------------------------------------------------------------------- verdicts
def test_studied_the_h0017_best_candidate_was_object_12_of_wang_2018(monkeypatch, tmp_path):
    asked = patch(monkeypatch, tmp_path)
    pa = prior_art(RA, DEC)
    # ADS is asked about SIMBAD's name and the NED name; no epoch was given, so nothing is moved
    assert asked == [(["2MASX J14240163+2950285", "WISEA J142401.66+295028.4"], [])] and asked.epochs == [None]
    assert pa["verdict"] == "studied" and pa["complete"] is True and pa["epoch"] is None
    assert pa["simbad"]["main_id"] == "2MASX J14240163+2950285" and pa["simbad"]["otype"] == "EmG"
    assert pa["ned"] == {"prefname": "WISEA J142401.66+295028.4", "type": "G", "z": 0.085530415, "z_bibcode": None,
                         "sep_arcsec": 0.03, "n_objects": 1, "names": ["WISEA J142401.66+295028.4"]}
    assert pa["n_papers"] == 5 and pa["n_topical"] == 2 and pa["n_about"] == 2  # 147 and 23 objects: about them
    assert [p["bibcode"] for p in pa["topical_papers"]] == ["2023PASP..135c4101G", WANG]  # newest first
    assert pa["topics"] == ["transient", "dimming", "infrared_excess", "binary"]  # None means every topic
    assert {k: v["status"] for k, v in pa["sources"].items()} == {"simbad": "ok", "ned": "ok", "ads": "ok",
                                                                  "catalogues": "empty"}
    assert pa["sources"]["ads"]["asked"] == ["2MASX J14240163+2950285", "WISEA J142401.66+295028.4"]
    assert pa["shelf_hits"] == [] and pa["otype_hits"] == [] and pa["catalogue_hits"] == [] and pa["nearby"] is None
    assert (pa["ra"], pa["dec"], pa["radius_arcsec"]) == (RA, DEC, 5.0) and len(pa["reasons"]) == 1
    assert pa["summary"] == ("Studied: 2 of 5 papers on 2MASX J14240163+2950285 match the topics (transient, dimming, "
                             "infrared_excess, binary); the newest is 2023PASP..135c4101G, \"A Census of Archival X-Ray "
                             "Spectra for Modeling Tidal Disruption Events\".")


def test_catalogued_an_object_with_papers_and_none_on_the_topic(monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok()))
    pa = prior_art(RA, DEC)
    assert pa["verdict"] == "catalogued" and pa["complete"] is True and pa["n_papers"] == 3 and pa["topical_papers"] == []
    assert pa["reasons"] == []
    assert pa["summary"] == ("Catalogued: 2MASX J14240163+2950285 is listed in 3 papers, and no title matches the topics "
                             "(transient, dimming, infrared_excess, binary).")
    # the same papers are "studied" or not depending on the topics asked for: Wang et al. is about a decline and dust
    patch(monkeypatch, tmp_path)
    assert prior_art(RA, DEC, topics=["binary"])["verdict"] == "catalogued"
    assert prior_art(RA, DEC, topics="dimming")["verdict"] == "catalogued"
    pa = prior_art(RA, DEC, topics=["infrared_excess"])
    assert pa["verdict"] == "studied" and [p["bibcode"] for p in pa["topical_papers"]] == [WANG]
    assert "1 of 5 papers on 2MASX J14240163+2950285 matches the topics (infrared_excess)" in pa["summary"]
    with pytest.raises(ValueError, match="unknown topic"):
        prior_art(RA, DEC, topics=["aliens"])


def test_unlisted_nothing_in_simbad_ned_or_the_shelves(monkeypatch, tmp_path):
    asked = patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED)
    pa = prior_art(106.2231, -42.8842)
    assert pa["verdict"] == "unlisted" and pa["complete"] is True and pa["n_papers"] == 0
    assert pa["simbad"] is None and pa["ned"] is None and asked == []  # no object: nothing to ask ADS
    # ... and that is "not asked", not ADS answering "no papers"; it does not make the answer incomplete
    assert pa["sources"]["ads"]["status"] == "not_asked" and "no SIMBAD or NED object" in pa["sources"]["ads"]["notes"][0]
    assert pa["summary"] == "Unlisted: no SIMBAD object, no NED object and no shelf entry within 5\"."


# ----------------------------------------------------------------------------- a source that did not answer
def test_no_ads_token_is_unavailable_not_empty(monkeypatch, tmp_path):
    monkeypatch.delenv("ADS_TOKEN", raising=False)
    monkeypatch.setattr(librarian, "ADS_TOKEN_FILE", tmp_path / "no-such-token")
    monkeypatch.setattr(librarian, "request", lambda *a, **k: pytest.fail("no request without a token"))
    papers, prov = librarian.ads_papers("WISEA J142401.66+295028.4")
    assert papers == [] and prov.status == "unavailable" and "no ADS token" in prov.notes[0]


def test_incomplete_is_reported_and_the_verdict_is_not_final(monkeypatch, tmp_path):
    # ADS down, and SIMBAD's list without Wang et al.: the sources that answered say "catalogued", which is not the truth
    down = ([], ok(status="unavailable", notes=["no ADS token (set ADS_TOKEN or write it to ~/.config/oddsky/ads-token)"]))
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=down)
    pa = prior_art(RA, DEC)
    assert pa["complete"] is False and pa["verdict"] == "catalogued" and pa["sources"]["ads"]["status"] == "unavailable"
    assert pa["summary"].startswith("Not final (ADS could not be queried); so far catalogued: ")

    # SIMBAD down: NED and ADS still find the paper, and the answer still says SIMBAD was not asked
    patch(monkeypatch, tmp_path, simbad=(dict(NO_SIMBAD[0]),
                                         ok(status="unavailable", notes=["simbad.harvard.edu unavailable after 2 attempts"])))
    pa = prior_art(RA, DEC)
    assert pa["complete"] is False and pa["verdict"] == "studied" and pa["simbad"] is None
    assert pa["summary"].startswith("Not final (SIMBAD could not be queried); so far studied: 1 of 3 papers on "
                                    "WISEA J142401.66+295028.4 matches")

    # NED down: ADS could not be asked either, and nothing found is not "unlisted" as a fact
    asked = patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NED_DOWN)
    pa = prior_art(RA, DEC)
    assert asked == [] and pa["complete"] is False and pa["verdict"] == "unlisted"
    assert pa["sources"]["ned"]["status"] == "unavailable" and pa["sources"]["ads"]["status"] == "unavailable"
    assert pa["summary"] == ("Not final (NED and ADS could not be queried); so far unlisted: the sources that answered "
                             "hold nothing within 5\".")


def test_a_failed_query_is_unavailable_and_a_header_alone_is_empty(monkeypatch):
    def down(*a, **k):
        raise RuntimeError("simbad.harvard.edu unavailable after 2 attempts")
    monkeypatch.setattr(librarian, "request", down)
    out, prov = librarian.simbad(RA, DEC)
    assert out["object"] is None and prov.status == "unavailable" and "unavailable after 2 attempts" in prov.notes[0]
    assert librarian.ned(RA, DEC)[1].status == "unavailable"

    class Html:
        text = "<html>Service temporarily unavailable</html>"
    monkeypatch.setattr(librarian, "request", lambda *a, **k: Html)
    assert librarian.simbad(RA, DEC)[1].status == "unavailable" and librarian.ned(RA, DEC)[1].status == "unavailable"

    class Header:
        text = "oid,main_id,otype,ra,dec,pmra,pmdec,nbref\n"
    monkeypatch.setattr(librarian, "request", lambda *a, **k: Header)
    out, prov = librarian.simbad(RA, DEC)
    assert out == NO_SIMBAD[0] and prov.status == "empty"


NED_HEADER = ("prefname,ra,dec,uncmaja,uncmina,uncposa,gallon,gallat,pos_bibcode,prefphytype,z,zunc,z_bibcode,zflag,"
              "n_crosref,n_notes,n_gphot,n_posd,n_zdf,n_ddf,n_dist,n_class,n_images,n_spectra,objid,type_key\n")
NED_ROW = ('"WISEA J142401.66+295028.4",216.0069291,29.8412329,0.09075,0.0895,90.0,46.0039122899956,'
           '69.5098133411628,"2013wise.rept....1C","G",0.085530415,1.05051395E-5,"2016SDSSD.C...0000:","SLS",'
           "29,0,58,11,9,6,0,0,1,1,2624218,55\n")
NED_FAR_ROW = ('"WISEA J142401.69+295011.9",216.0070539,29.8366522,0.39775,0.36775,0.0,45.9908233210418,69.5098574493103,'
               '"2013wise.rept....1C","G",,,,,5,0,51,6,0,4,0,0,0,0,90003210,55\n')  # 16.4" south: outside 5", inside 30"
SIMBAD_HEADER = "oid,main_id,otype,ra,dec,pmra,pmdec,nbref\n"


class Resp:
    def __init__(self, text=None, payload=None):
        self.text, self._p = text, payload

    def json(self):
        return self._p


def test_the_services_are_read_as_they_answered_on_2026_11_05(monkeypatch):
    """The CSV each TAP service returned for RA 216.0069, Dec 29.8412, and the query shapes sent."""
    sent = []

    def fake(method, url, **kw):
        q = (kw.get("data") or kw.get("params"))["QUERY"]
        sent.append((method, url, q))
        if "NEDTAP" in q:
            return Resp(NED_HEADER + NED_FAR_ROW + NED_ROW)
        if "has_ref" in q:
            return Resp("oidref,bibcode,title,nbobject\n"
                        + "".join(f'2250411,"{p["bibcode"]}","{p["title"]}",{p["n_objects"]}\n' for p in SIMBAD_PAPERS))
        return Resp(SIMBAD_HEADER + '2250411,"2MASX J14240163+2950285","EmG",216.00692860053996,29.84119873223,,,5\n')

    monkeypatch.setattr(librarian, "request", fake)
    out, prov = librarian.simbad(RA, DEC)
    assert prov.status == "ok" and prov.rows_kept == 5 and out["n_objects"] == 1 and out["nearby"] is None
    assert out["object"]["main_id"] == "2MASX J14240163+2950285" and out["object"]["otype"] == "EmG"
    assert out["object"]["sep_arcsec"] < 0.2 and out["object"]["n_refs"] == 5 and out["nearest"] == out["object"]
    assert out["papers"] == SIMBAD_PAPERS  # with the number of objects each paper lists
    got, prov = librarian.ned(RA, DEC)
    obj = got["object"]
    assert prov.status == "ok" and obj["prefname"] == "WISEA J142401.66+295028.4" and obj["type"] == "G"
    assert abs(obj["z"] - 0.0855) < 1e-4 and obj["sep_arcsec"] < 0.2 and obj["z_bibcode"] == "2016SDSSD.C...0000:"
    assert obj["n_objects"] == 1 and [o["prefname"] for o in got["objects"]] == ["WISEA J142401.66+295028.4"]  # not the far one
    (m1, u1, q1), (m2, u2, q2), (m3, u3, q3) = sent
    # the cone sent is 30" (0.0083333 deg), so that the nearest object can be named when nothing lies within the 5" asked
    cone = "CIRCLE('ICRS',216.0069000,29.8412000,0.0083333))=1"
    assert (m1, u1) == (m2, u2) == ("POST", "https://simbad.harvard.edu/simbad/sim-tap/sync")
    assert q1 == f"SELECT oid, main_id, otype, ra, dec, pmra, pmdec, nbref FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),{cone}"
    assert q2 == ("SELECT oidref, bibcode, title, nbobject FROM has_ref JOIN ref ON oidbib=oidbibref "
                  "WHERE oidref IN (2250411)")
    assert "ORDER BY" not in q1 + q2 and " AS " not in q1 + q2  # this SIMBAD mirror rejects both
    assert (m3, u3) == ("GET", "https://ned.ipac.caltech.edu/tap/sync")
    assert q3 == ("SELECT * FROM NEDTAP.objdir WHERE CONTAINS(POINT('J2000',ra,dec),"
                  "CIRCLE('J2000',216.0069000,29.8412000,0.0083333))=1")


def test_ads_is_asked_with_each_name_and_the_token_never_leaves_the_header(monkeypatch):
    monkeypatch.setenv("ADS_TOKEN", "s3cret-token")
    sent = []
    translated = '((=abs:"WISEA J142401.66+295028.4" OR simbid:"0" OR nedid:"WISEA_J142401.66+295028.4") database:astronomy)'

    def fake(method, url, **kw):
        sent.append((method, url, kw))
        if url.endswith("/objects/query"):
            return Resp(payload={"query": translated})
        return Resp(payload={"response": {"numFound": 3, "docs": [dict(p, title=[p["title"]]) for p in ADS_PAPERS]}})

    monkeypatch.setattr(librarian, "request", fake)
    papers, prov = librarian.ads_papers("WISEA J142401.66+295028.4")
    assert prov.status == "ok" and papers == ADS_PAPERS  # ADS gives the title as a list; the first is kept
    assert prov.notes == []  # ADS knew the name: it gave a NED id
    (m1, u1, k1), (m2, u2, k2) = sent
    assert (m1, u1) == ("POST", "https://api.adsabs.harvard.edu/v1/objects/query")
    assert k1["json"] == {"query": ['object:"WISEA J142401.66+295028.4"']}
    assert (m2, u2) == ("GET", "https://api.adsabs.harvard.edu/v1/search/query")
    assert k2["params"] == {"q": translated, "fl": "bibcode,title,year", "sort": "date desc", "rows": 200}
    assert k1["headers"] == k2["headers"] == {"Authorization": "Bearer s3cret-token"}
    assert "s3cret" not in prov.model_dump_json()

    # several names: one translation each (ADS translates only the first of a list), searched together with the paper
    # NED gives as the source of the redshift
    sent.clear()
    papers, prov = librarian.ads_papers(["KT Eri", "WISEA J044754.20-101042.7"], ["2016SDSSD.C...0000:"])
    asked = sorted(k["json"]["query"][0] for m, u, k in sent if u.endswith("/objects/query"))
    assert asked == ['object:"KT Eri"', 'object:"WISEA J044754.20-101042.7"']
    assert [k["params"]["q"] for m, u, k in sent if u.endswith("/search/query")] == [
        f'{translated} OR {translated} OR bibcode:"2016SDSSD.C...0000:"']

    def leaky(method, url, **kw):
        raise RuntimeError("401 for token s3cret-token")
    monkeypatch.setattr(librarian, "request", leaky)
    papers, prov = librarian.ads_papers("WISEA J142401.66+295028.4")
    assert prov.status == "unavailable" and "s3cret" not in prov.notes[0] and "<token>" in prov.notes[0]

    monkeypatch.setattr(librarian, "request", lambda m, u, **k: Resp(payload={"query": translated} if u.endswith("/objects/query")
                                                                    else {"response": {"numFound": 0, "docs": []}}))
    assert librarian.ads_papers("known to NED, no papers")[1].status == "empty"


def test_ads_not_asked_and_unresolved_are_not_empty(monkeypatch, tmp_path):
    """ADS answers `simbid:"0"` for a name it does not know (2026-11-05: for every name; `nedid` is filled when NED knows
    it). With no identifier the search is only for the name as text in abstracts: finding nothing is then not an answer."""
    monkeypatch.setenv("ADS_TOKEN", "t")
    unknown = '((=abs:"Barnard\'s star" OR simbid:"0" OR nedid:"0") database:astronomy)'
    known = '((=abs:"KT Eri" OR simbid:"0" OR nedid:"WISEA_J044754.20-101042.7") database:astronomy)'
    assert not librarian._ads_resolved(unknown) and librarian._ads_resolved(known)
    assert not librarian._ads_resolved('((=abs:"x" OR simbid:"0") database:astronomy)')
    assert librarian._ads_resolved('((=abs:"x" OR simbid:"1471968" OR nedid:"0") database:astronomy)')
    docs = []

    def fake(method, url, **kw):
        if url.endswith("/objects/query"):
            return Resp(payload={"query": known if "KT Eri" in kw["json"]["query"][0] else unknown})
        return Resp(payload={"response": {"numFound": len(docs), "docs": docs}})

    monkeypatch.setattr(librarian, "request", fake)
    papers, prov = librarian.ads_papers(["Barnard's star"])
    assert papers == [] and prov.status == "unresolved"
    assert prov.notes == ['ADS did not recognise "Barnard\'s star" as an object (simbid:"0", no NED id): for that name only '
                          "the text of abstracts was searched"]
    assert librarian.ads_papers(["Barnard's star", "KT Eri"])[1].status == "empty"  # one name was known: ADS did answer
    docs.append({"bibcode": "2019ApJ...875L..12A", "title": ["Breezing through the Space Environment of Barnard's Star b"]})
    papers, prov = librarian.ads_papers(["Barnard's star"])
    assert prov.status == "ok" and len(papers) == 1 and "did not recognise" in prov.notes[0]  # found in an abstract

    monkeypatch.setattr(librarian, "request", lambda *a, **k: pytest.fail("nothing to ask: no request"))
    papers, prov = librarian.ads_papers([])
    assert papers == [] and prov.status == "not_asked" and "no object name" in prov.notes[0]

    # in prior_art: "unresolved" is said in the summary of a "catalogued" answer, and does not make it incomplete
    patch(monkeypatch, tmp_path, simbad=sim([], main_id="NAME Barnard's star", otype="BY*"), ned=NO_NED,
          ads=([], ok(status="unresolved", notes=["ADS did not recognise ..."])))
    pa = prior_art(RA, DEC)
    assert pa["verdict"] == "catalogued" and pa["complete"] is True and pa["sources"]["ads"]["status"] == "unresolved"
    assert pa["summary"] == ("Catalogued: NAME Barnard's star is in the archives with no paper attached; ADS did not "
                             "recognise the name, so only the text of its abstracts was searched.")


def test_ads_is_asked_for_simbads_name_and_every_ned_name_and_neds_redshift_paper_is_a_paper(monkeypatch, tmp_path):
    assert librarian.ads_name("NAME Barnard's star") == "Barnard's star" and librarian.ads_name("V* KT Eri") == "KT Eri"
    assert librarian.ads_name("* alf Lyr") == "alf Lyr" and librarian.ads_name("EM* AS 209") == "AS 209"
    assert librarian.ads_name("2MASX J14240163+2950285") == "2MASX J14240163+2950285" and librarian.ads_name("M 100") == "M 100"
    second = {**NED_OBJ, "prefname": "SDSS J142401.65+295028.5", "z": None, "sep_arcsec": 0.4}
    zbib = "2009ApJS..180...67R"
    asked = patch(monkeypatch, tmp_path, simbad=sim(QUIET, main_id="V* KT Eri"), ned=ned_is({**NED_OBJ, "z_bibcode": zbib}, second),
                  ads=([{"bibcode": zbib, "title": "Photometric redshifts of quasar candidates", "year": "2009"}], ok()))
    pa = prior_art(RA, DEC)
    assert asked == [(["KT Eri", "WISEA J142401.66+295028.4", "SDSS J142401.65+295028.5"], [zbib])]
    assert pa["ned"]["names"] == ["WISEA J142401.66+295028.4", "SDSS J142401.65+295028.5"] and pa["ned"]["n_objects"] == 2
    assert pa["ned"]["z_bibcode"] == zbib and pa["n_papers"] == 4  # SIMBAD's three and the paper NED's redshift is from

    # with ADS down the redshift paper is still listed, by bibcode alone, as NED's
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is({**NED_OBJ, "z_bibcode": zbib}),
          ads=([], ok(status="unavailable", notes=["no ADS token"])))
    pa = prior_art(RA, DEC)
    assert pa["n_papers"] == 1 and pa["verdict"] == "catalogued" and pa["complete"] is False

    # more names than ADS_MAX_NAMES: the first are asked, and the note says how many were not
    many = [{**NED_OBJ, "prefname": f"NGC 4321:[LMD2020] {c}", "sep_arcsec": i} for i, c in enumerate("ABCDEFGH")]
    asked = patch(monkeypatch, tmp_path, simbad=sim(main_id="M 100"), ned=ned_is(*many))
    pa = prior_art(RA, DEC)
    assert len(asked[0][0]) == librarian.ADS_MAX_NAMES == 6 and asked[0][0][0] == "M 100"
    assert pa["sources"]["ads"]["notes"] == ["3 more NED names in the cone were not put to ADS"]


def test_ads_truncation_is_not_complete_and_says_so(monkeypatch, tmp_path):
    """NGC 4472 has 1373 papers in ADS; reading stops at ADS_MAX_ROWS, and the answer must not look complete."""
    monkeypatch.setenv("ADS_TOKEN", "t")
    monkeypatch.setattr(librarian, "ADS_MAX_ROWS", 4)
    monkeypatch.setattr(librarian, "ADS_ROWS", 2)
    starts = []

    def fake(method, url, **kw):
        if url.endswith("/objects/query"):
            return Resp(payload={"query": 'nedid:"NGC_4472"'})
        start = kw["params"].get("start", 0)
        starts.append(start)
        return Resp(payload={"response": {"numFound": 1373, "docs": [
            {"bibcode": f"20{20 - start - i:02d}ApJ...{start + i:03d}....1X", "title": ["A quiet title"]} for i in range(2)]}})

    monkeypatch.setattr(librarian, "request", fake)
    papers, prov = librarian.ads_papers("NGC 4472")
    assert starts == [0, 2] and len(papers) == 4 and prov.status == "ok" and (prov.rows_raw, prov.rows_kept) == (1373, 4)
    assert prov.notes == ["ADS holds 1373 papers; only the newest 4 were read"]

    cut = ok(rows_raw=1373, rows_kept=1000, notes=["ADS holds 1373 papers; only the newest 1000 were read"])
    patch(monkeypatch, tmp_path, simbad=sim(QUIET, main_id="M 49"), ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], cut))
    pa = prior_art(RA, DEC)
    assert pa["complete"] is False and pa["verdict"] == "catalogued" and librarian.unavailable_names(pa) == []
    assert pa["sources"]["ads"]["truncated"] == {"found": 1373, "read": 1000}
    assert librarian.incomplete_reasons(pa) == ["ADS holds 1373 papers and only the newest 1000 were read"]
    assert pa["summary"] == ("Not final (ADS holds 1373 papers and only the newest 1000 were read); so far catalogued: M 49 is "
                             "listed in 3 papers, and no title matches the topics (transient, dimming, infrared_excess, binary).")
    patch(monkeypatch, tmp_path)
    assert prior_art(RA, DEC)["sources"]["ads"]["truncated"] is None


# ----------------------------------------------------------------------------- proper motion and geometry
BARNARD = '2669393,"NAME Barnard\'s star","BY*",269.4520769586187,4.693364966576667,-801.551,10362.394,924\n'
BARNARD_B = '13596720,"NAME Barnard\'s Star b","Pl",269.4520769586187,4.693364966576667,-801.551,10362.394,34\n'
GES = '24052694,"GES J17574778+0443542","*",269.4490799999999,4.731720000000001,,,3\n'  # 29" from the 2010.5 position
B2010 = (269.449731, 4.723589)  # Barnard's Star at 2010.5: 108.8" north and 8.4" west of its J2000 position


def test_a_star_is_found_where_its_proper_motion_puts_it_at_the_epoch(monkeypatch):
    """Barnard's Star at its AllWISE-epoch position was "catalogued ... with no paper attached": SIMBAD's position is for
    J2000, 109" away. With the epoch a second cone finds stars fast enough to have crossed into the first."""
    sent = []

    def fake(method, url, **kw):
        q = kw["data"]["QUERY"]
        sent.append(q)
        if "has_ref" in q:
            return Resp("oidref,bibcode,title,nbobject\n"
                        '2669393,"2018Natur.563..365R","A candidate super-Earth planet orbiting near the snow line of Barnard\'s star.",1\n')
        return Resp(SIMBAD_HEADER + (BARNARD + BARNARD_B if "pmra*pmra" in q else GES))

    monkeypatch.setattr(librarian, "request", fake)
    out, prov = librarian.simbad(*B2010, 5.0, epoch=2010.5)
    assert prov.status == "ok" and prov.query["epoch"] == 2010.5 and out["n_objects"] == 2
    # the star, not its planet at the same place: the object with the most references names the position
    assert out["object"]["main_id"] == "NAME Barnard's star" and out["object"]["n_refs"] == 924
    assert out["object"]["sep_arcsec"] < 0.3  # at 2010.5; the catalogued (J2000) position is kept as it is
    assert abs(out["object"]["dec"] - 4.693365) < 1e-6 and [p["bibcode"] for p in out["papers"]] == ["2018Natur.563..365R"]
    plain, wide, refs = sent
    assert "pmra*pmra" not in plain and "CIRCLE('ICRS',269.4497310,4.7235890,0.0083333)" in plain
    # 5" + 11"/yr x 10.5 yr = 120.5" (0.0334722 deg); only a star faster than (30" - 5") / 10.5 yr = 2381 mas/yr can have
    # come from outside the first cone
    assert wide == ("SELECT oid, main_id, otype, ra, dec, pmra, pmdec, nbref FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),"
                    "CIRCLE('ICRS',269.4497310,4.7235890,0.0334722))=1 AND pmra*pmra+pmdec*pmdec > 5668934")
    assert refs.endswith("WHERE oidref IN (2669393, 13596720)") or refs.endswith("WHERE oidref IN (13596720, 2669393)")

    # without an epoch nothing is moved and no second cone is sent: today's behaviour
    sent.clear()
    out, prov = librarian.simbad(*B2010, 5.0)
    assert len(sent) == 1 and prov.status == "empty" and out["object"] is None and "epoch" not in prov.query
    assert out["nearby"]["main_id"] == "GES J17574778+0443542" and 28 < out["nearby"]["sep_arcsec"] < 30

    # a slow star inside the first cone is moved too: 12" south at J2000 with 1"/yr northward is 1.5" away at 2010.5
    slow = f'77,"LP 1-1","PM*",10.0,{-20.0 - 12 / 3600},0.0,1000.0,7\n'
    monkeypatch.setattr(librarian, "request", lambda m, u, **kw: Resp(
        "oidref,bibcode,title,nbobject\n" if "has_ref" in kw["data"]["QUERY"] else
        SIMBAD_HEADER + ("" if "pmra*pmra" in kw["data"]["QUERY"] else slow)))
    out, prov = librarian.simbad(10.0, -20.0, 5.0, epoch=2010.5)
    assert out["object"]["main_id"] == "LP 1-1" and abs(out["object"]["sep_arcsec"] - 1.5) < 0.01
    out, prov = librarian.simbad(10.0, -20.0, 5.0)
    assert out["object"] is None and abs(out["nearby"]["sep_arcsec"] - 12.0) < 0.01
    # epoch 2000: no motion, and no second query
    assert librarian.simbad(10.0, -20.0, 5.0, epoch=2000.0)[0]["object"] is None


def test_prior_art_passes_the_epoch_on(monkeypatch, tmp_path):
    asked = patch(monkeypatch, tmp_path)
    pa = prior_art(RA, DEC, 5.0, "transient", epoch=2010.5)
    assert asked.epochs == [2010.5] and pa["epoch"] == 2010.5
    prior_art(RA, DEC, 5.0, "transient", 2015.0)  # positional, after topics
    assert asked.epochs == [2010.5, 2015.0]


def test_separation_is_a_haversine_right_at_the_poles_and_across_ra_zero():
    sep = librarian._sep_arcsec
    # 10" from the pole on opposite sides of it: 20" apart, not the 3 degrees a flat formula gives
    d = 90.0 - 10.0 / 3600
    assert abs(sep(0.0, d, 180.0, d) - 20.0) < 1e-6
    assert abs(sep(0.0, d, 90.0, d) - 10.0 * math.sqrt(2)) < 1e-4
    assert abs(sep(37.0, 90.0, 255.0, d) - 10.0) < 1e-6 and abs(sep(10.0, -90.0, 200.0, -d) - 10.0) < 1e-6
    assert abs(sep(359.9999, 0.0, 0.0002, 0.0) - 1.08) < 1e-6           # across RA = 0
    assert abs(sep(RA, DEC, RA + 3.0 / 3600 / math.cos(math.radians(DEC)), DEC) - 3.0) < 1e-4
    assert sep(RA, DEC, RA, DEC) == 0.0 and abs(sep(0.0, 0.0, 180.0, 0.0) - 648000.0) < 1e-3
    # proper motion along a great circle: straight over the pole, and back again
    ra, dec = librarian._moved(0.0, d, 0.0, 20000.0, 1.0)  # 20" north from 10" short of the pole
    assert abs(ra - 180.0) < 1e-6 and abs(dec - d) < 1e-9
    ra, dec = librarian._moved(*B2010, 801.551, -10362.394, 10.5)
    assert sep(ra, dec, 269.4520769586187, 4.693364966576667) < 0.01
    assert librarian._moved(10.0, 20.0, 0.0, 0.0, 10.0) == (10.0, 20.0)


def test_with_nothing_inside_the_radius_the_nearest_object_within_30_arcsec_is_named(monkeypatch, tmp_path):
    """7" from Swift J1644+57 the answer was "Unlisted", complete. It still is unlisted, and now says what is next door."""
    swift = {"main_id": "Swift J164449.3+573451", "otype": "gB", "ra": 251.2054, "dec": 57.5808, "sep_arcsec": 7.03, "n_refs": 412}
    far = {"prefname": "WISEA J164449.94+573451.4", "type": "G", "z": None, "z_bibcode": None, "ra": 251.2081, "dec": 57.5809,
           "sep_arcsec": 11.4}
    asked = patch(monkeypatch, tmp_path, simbad=({**NO_SIMBAD[0], "nearby": swift}, ok(status="empty")), ned=ned_is(nearby=far))
    pa = prior_art(251.2054, 57.5827)
    assert pa["verdict"] == "unlisted" and pa["complete"] is True and asked == []  # the neighbour's papers are not read
    assert pa["nearby"] == {"source": "SIMBAD", "name": "Swift J164449.3+573451", "type": "gB", "sep_arcsec": 7.03}
    assert pa["otype_hits"] == []  # a transient type outside the radius is named, and is not a verdict
    assert pa["summary"] == ("Unlisted: no SIMBAD object, no NED object and no shelf entry within 5\"; the nearest is "
                             "Swift J164449.3+573451 (SIMBAD), 7.0\" away.")
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is(nearby=far))
    assert prior_art(251.2054, 57.5827)["nearby"]["name"] == "WISEA J164449.94+573451.4"
    # with an object inside the radius in either archive there is nothing to add
    patch(monkeypatch, tmp_path, simbad=({**NO_SIMBAD[0], "nearby": swift}, ok(status="empty")))
    pa = prior_art(RA, DEC)
    assert pa["nearby"] is None and pa["verdict"] != "unlisted"

    # read from NED's answer: the object 16.4" away is the neighbour, not the object
    monkeypatch.undo()
    monkeypatch.setattr(librarian, "request", lambda *a, **k: Resp(NED_HEADER + NED_FAR_ROW))
    got, prov = librarian.ned(RA, DEC)
    assert prov.status == "empty" and got["object"] is None and got["objects"] == []
    assert got["nearby"]["prefname"] == "WISEA J142401.69+295011.9" and abs(got["nearby"]["sep_arcsec"] - 16.4) < 0.1


def test_the_object_with_the_most_references_names_the_position_and_the_nearest_is_kept(monkeypatch, tmp_path):
    """NGC 4472's summary named "[MKZ2003] XID 71", an X-ray source 0.4" from the nucleus."""
    rows = ('9,"[MKZ2003] XID 71","X",187.44490,8.00050,,,2\n'
            '8,"M 49","Sy2",187.44484,8.00048,,,2478\n'
            '7,"[CFG2019] far","GlC",187.45200,8.00048,,,1\n')
    monkeypatch.setattr(librarian, "request", lambda m, u, **kw: Resp(
        "oidref,bibcode,title,nbobject\n" if "has_ref" in kw["data"]["QUERY"] else SIMBAD_HEADER + rows))
    out, prov = librarian.simbad(187.44492, 8.00051)
    assert out["n_objects"] == 2 and [o["main_id"] for o in out["objects"]] == ["[MKZ2003] XID 71", "M 49"]
    assert out["object"]["main_id"] == "M 49" and out["nearest"]["main_id"] == "[MKZ2003] XID 71" and out["nearby"] is None

    xid, m49 = out["objects"]
    monkeypatch.undo()
    patch(monkeypatch, tmp_path, simbad=({**out, "papers": QUIET}, ok()), ads=([], ok(status="empty")))
    pa = prior_art(187.44492, 8.00051)
    assert pa["simbad"]["main_id"] == "M 49" and pa["simbad"]["n_refs"] == 2478 and pa["simbad"]["n_objects"] == 2
    assert pa["simbad"]["nearest"] == {"main_id": "[MKZ2003] XID 71", "otype": "X", "sep_arcsec": xid["sep_arcsec"]}
    assert pa["summary"].startswith("Catalogued: M 49 is listed in 3 papers") and pa["sources"]["ads"]["asked"][0] == "M 49"


# ----------------------------------------------------------------------------- four verdicts
BIG = {"bibcode": "2019ApJ...887..169F", "n_objects": 4361, "title": "A measurement of the supernova rate in 4000 galaxies"}
UGC = {"bibcode": "1973UGC...C...0000N", "n_objects": 12939,
       "title": "Uppsala General Catalogue of Galaxies. Acta Universitatis Upsaliensis, Nova Regiae Societatis"}


def test_mentioned_topical_titles_only_in_papers_that_list_hundreds_of_objects(monkeypatch, tmp_path):
    """11 of 11 ordinary stars and galaxies were "studied": rate papers attached to thousands of galaxies, the UGC's own
    title. SIMBAD's ref.nbobject tells a paper about the object from a list it is in."""
    quiet_ads = ([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok())
    patch(monkeypatch, tmp_path, simbad=sim([*QUIET, BIG, UGC], main_id="NGC 821"), ads=quiet_ads)
    pa = prior_art(RA, DEC, topics="transient")
    assert pa["verdict"] == "mentioned" and pa["complete"] is True and pa["reasons"] == []
    assert (pa["n_papers"], pa["n_topical"], pa["n_about"]) == (5, 2, 0)
    assert [(p["bibcode"], p["n_objects"], p["big_list"]) for p in pa["topical_papers"]] == [
        ("2019ApJ...887..169F", 4361, True), ("1973UGC...C...0000N", 12939, True)]
    assert pa["summary"] == ("Mentioned: 2 of 5 papers on NGC 821 match the topics (transient), all of them lists of more "
                             "than 500 objects; the newest is 2019ApJ...887..169F, \"A measurement of the supernova rate in "
                             "4000 galaxies\".")
    patch(monkeypatch, tmp_path, simbad=sim([*QUIET, BIG]), ads=quiet_ads)
    assert "1 of 4 papers on 2MASX J14240163+2950285 matches the topics (transient), a list of more than 500 objects; " in \
        prior_art(RA, DEC, topics="transient")["summary"]

    # the threshold: a paper on 500 objects is about them (a census of a hundred hosts is), one on 501 is a list
    assert librarian.ABOUT_MAX_OBJECTS == 500
    for n, verdict in ((1, "studied"), (147, "studied"), (500, "studied"), (501, "mentioned"), (None, "studied")):
        patch(monkeypatch, tmp_path, simbad=sim([*QUIET, {**BIG, "n_objects": n}]), ads=quiet_ads)
        assert prior_art(RA, DEC, topics="transient")["verdict"] == verdict, n

    # one paper about the object is enough, and the lists are not counted with it
    patch(monkeypatch, tmp_path, simbad=sim([*SIMBAD_PAPERS, BIG, UGC]))
    pa = prior_art(RA, DEC, topics="transient")
    assert pa["verdict"] == "studied" and (pa["n_topical"], pa["n_about"]) == (4, 2)
    assert pa["summary"] == ("Studied: 2 of 7 papers on 2MASX J14240163+2950285 match the topics (transient), not counting 2 "
                             "lists of more than 500 objects; the newest is 2023PASP..135c4101G, \"A Census of Archival "
                             "X-Ray Spectra for Modeling Tidal Disruption Events\".")

    # a paper only ADS lists has no object count: it is taken to be about the object
    only_ads = {"bibcode": "2024ATel16543....1X", "title": "A nuclear outburst in a quiet galaxy", "year": "2024"}
    patch(monkeypatch, tmp_path, simbad=sim([*QUIET, BIG]), ads=([only_ads], ok()))
    pa = prior_art(RA, DEC, topics="transient")
    assert pa["verdict"] == "studied" and pa["n_about"] == 1 and pa["topical_papers"][0]["n_objects"] is None
    # ... and SIMBAD's count wins when both list the paper
    patch(monkeypatch, tmp_path, simbad=sim([*QUIET, BIG]), ads=([{"bibcode": BIG["bibcode"], "title": BIG["title"]}], ok()))
    pa = prior_art(RA, DEC, topics="transient")
    assert pa["verdict"] == "mentioned" and pa["topical_papers"][0]["sources"] == ["simbad", "ads"]


def test_a_transient_object_type_is_studied_whatever_the_titles_say(monkeypatch, tmp_path):
    assert {"SN*", "No*", "ev"} <= set(librarian.TRANSIENT_OTYPES) and "EmG" not in librarian.TRANSIENT_OTYPES
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in librarian.TRANSIENT_OTYPES.items())  # plain data
    quiet = [{"bibcode": "2010IBVS.5925....1X", "n_objects": 3, "title": "Photometry of three stars"}]
    patch(monkeypatch, tmp_path, simbad=sim(quiet, main_id="V* KT Eri", otype="No*", sep_arcsec=0.1), ned=NO_NED, ads=([], ok(status="empty")))
    pa = prior_art(71.9750, -10.1786, topics="dimming")
    assert pa["verdict"] == "studied" and pa["n_topical"] == 0
    assert pa["otype_hits"] == [{"main_id": "V* KT Eri", "otype": "No*", "label": "nova", "sep_arcsec": 0.1}]
    assert pa["summary"] == "Studied: SIMBAD has a nova here, V* KT Eri (No*)."

    # any object within the radius counts, not only the one that names the position: a supernova in a galaxy
    m100 = {**SIMBAD_OBJ, "main_id": "M 100", "otype": "AGN", "n_refs": 2990, "sep_arcsec": 2.6}
    sn = {**SIMBAD_OBJ, "main_id": "SN 2020oi", "otype": "SN*", "n_refs": 60, "sep_arcsec": 4.7}
    ev = {**SIMBAD_OBJ, "main_id": "AT 2019xyz", "otype": "ev", "n_refs": 1, "sep_arcsec": 4.9}
    patch(monkeypatch, tmp_path, simbad=({"object": m100, "nearest": m100, "n_objects": 3, "objects": [m100, sn, ev],
                                          "papers": QUIET, "nearby": None}, ok()), ads=([], ok(status="empty")))
    pa = prior_art(185.7283, 15.8224, topics="binary")
    assert pa["verdict"] == "studied" and [o["otype"] for o in pa["otype_hits"]] == ["SN*", "ev"]
    assert pa["summary"] == "Studied: SIMBAD has a supernova here, SN 2020oi (SN*) and 1 more."
    patch(monkeypatch, tmp_path, simbad=sim(QUIET, otype="EmG"), ads=([], ok(status="empty")))
    assert prior_art(RA, DEC)["verdict"] == "catalogued"


# ----------------------------------------------------------------------------- the catalogues
VSX_HIT = {"object": "KT Eri", "class": "NR", "sep_arcsec": 2.94, "table": "B/vsx/vsx"}
VARWISE_HIT = {"object": "VarWISE J110629.07-443500.9", "class": "agn", "sep_arcsec": 0.13, "table": "varwiseext"}
MQ_HIT = {"object": "3C 273", "class": "QRX", "sep_arcsec": 0.07, "table": "VII/294/catalog"}
SECREST_HIT = {"object": "J110629.07-443500.9", "class": None, "sep_arcsec": 0.13, "table": "J/ApJS/221/12/table1"}
ASSEF_HIT = {"object": "J110629.07-443500.9", "class": None, "sep_arcsec": 0.13, "table": "J/ApJS/234/23/r90cat"}
ANON = {**NED_OBJ, "prefname": "WISEA J110629.07-443500.9", "type": None, "z": None}


def test_a_catalogue_of_variables_is_studied_and_an_agn_catalogue_is_reported(monkeypatch, tmp_path):
    """Three of H-0017's 31 are published NEOWISE variables in VarWISE and 26 are in Secrest et al. 2015; all read
    "catalogued". No bibliography shows membership of a large catalogue."""
    assert {c["key"]: c["kind"] for c in librarian.CATALOGUES} == {
        "vsx": "variable", "varwise": "variable", "milliquas": "agn", "secrest2015": "agn", "assef2018": "agn"}
    assert all(c["kind"] in librarian.CATALOGUE_KINDS and c["service"] in ("vizier", "irsa") and c["bibcode"] and c["table"]
               for c in librarian.CATALOGUES)  # plain data: a new catalogue is a new entry
    empty = ([], ok(status="empty"))

    # kind "variable": studied, with nothing else on the object (VarWISE, then VSX)
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is(ANON), ads=empty, catalogues=cats(varwise=[VARWISE_HIT]))
    pa = prior_art(166.6211, -44.5836, topics="transient")
    assert pa["verdict"] == "studied" and pa["complete"] is True and pa["n_papers"] == 0
    assert pa["catalogue_hits"] == [{"catalogue": "varwise", "name": "VarWISE", "kind": "variable",
                                     "bibcode": "2026ApJS..284...41P", **VARWISE_HIT, "n_hits": 1}]
    assert pa["sources"]["catalogues"]["status"] == "ok"
    assert pa["summary"] == "Studied: VarWISE lists a variable here, VarWISE J110629.07-443500.9 (type agn)."
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED, catalogues=cats(vsx=[VSX_HIT]))
    pa = prior_art(71.9750, -10.1786)
    assert pa["verdict"] == "studied" and pa["summary"] == "Studied: VSX lists a variable here, KT Eri (type NR)."

    # kind "agn": the verdict does not change, and the summary says where it is listed (each of the three)
    for key, hit, name in (("milliquas", MQ_HIT, "Milliquas"), ("secrest2015", SECREST_HIT, "Secrest et al. 2015"),
                           ("assef2018", ASSEF_HIT, "Assef et al. 2018")):
        patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is(ANON), ads=empty, catalogues=cats(**{key: [hit]}))
        pa = prior_art(166.6211, -44.5836, topics="transient")
        assert pa["verdict"] == "catalogued" and pa["complete"] is True and pa["reasons"] == []
        assert pa["catalogue_hits"][0]["kind"] == "agn" and pa["catalogue_hits"][0]["catalogue"] == key
        assert pa["summary"] == ("Catalogued: WISEA J110629.07-443500.9 is in the archives with no paper attached. It is "
                                 f"listed as an AGN or AGN candidate in {name}.")
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED, catalogues=cats(secrest2015=[SECREST_HIT], assef2018=[ASSEF_HIT]))
    pa = prior_art(166.6211, -44.5836)
    assert pa["verdict"] == "unlisted"
    assert pa["summary"] == ("Unlisted: no SIMBAD object, no NED object and no shelf entry within 5\". It is listed as an AGN "
                             "or AGN candidate in Secrest et al. 2015 and Assef et al. 2018.")

    # both kinds, on an object that is studied anyway: the variable is a reason, the AGN listing a second sentence
    patch(monkeypatch, tmp_path, catalogues=cats(varwise=[VARWISE_HIT], secrest2015=[SECREST_HIT]))
    pa = prior_art(RA, DEC, topics="transient")
    assert pa["verdict"] == "studied" and len(pa["reasons"]) == 2 and pa["reasons"][1].startswith("VarWISE lists a variable")
    assert pa["summary"].endswith("; VarWISE lists a variable here, VarWISE J110629.07-443500.9 (type agn). It is listed as "
                                  "an AGN or AGN candidate in Secrest et al. 2015.")


def test_a_catalogue_that_did_not_answer_is_named_and_the_verdict_is_not_final(monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is(ANON), ads=([], ok(status="empty")),
          catalogues=cats(varwise="unavailable", secrest2015=[SECREST_HIT]))
    pa = prior_art(166.6211, -44.5836)
    assert pa["complete"] is False and pa["verdict"] == "catalogued" and librarian.unavailable_names(pa) == ["VarWISE"]
    assert pa["sources"]["catalogues"]["status"] == "unavailable" and pa["sources"]["catalogues"]["notes"] == ["VarWISE: timeout"]
    assert [c["status"] for c in pa["catalogues"]] == ["empty", "unavailable", "empty", "ok", "empty"]
    assert pa["summary"] == ("Not final (VarWISE could not be queried); so far catalogued: WISEA J110629.07-443500.9 is in the "
                             "archives with no paper attached. It is listed as an AGN or AGN candidate in Secrest et al. 2015.")
    patch(monkeypatch, tmp_path, catalogues=cats(vsx="unavailable", assef2018="unavailable"),
          ads=([], ok(status="unavailable", notes=["no ADS token"])))
    assert librarian.unavailable_names(prior_art(RA, DEC)) == ["ADS", "VSX", "Assef et al. 2018"]


VIZIER_HEAD = ("#\n#   VizieR Astronomical Server vizier.cfa.harvard.edu\n#    Date: 2026-11-06T04:12:29 [V7.6.1]\n"
               "#INFO\tservice_protocol=ASU\t  IVOID of the protocol through which the data was retrieved\n\n")
VIZIER_VSX = (VIZIER_HEAD + "#RESOURCE=yCat_102027\n#Name: B/vsx\n#Title: AAVSO International Variable Star Index VSX (Watson+, 2006-)\n"
              "#Table\tB_vsx_vsx:\n#Name: B/vsx/vsx\n#Title: Variable Star indeX, Version 2026-10-18\n"
              "#Column\t_r\t(F4.2)\tDistance from center\t[ucd=pos.angDistance]\n"
              "#Column\tName\t(A30)\tVariable star identifier\t[ucd=meta.id;meta.main]\n"
              "_r\tOID\tName\tV\tRAJ2000\tDEJ2000\tType\n"
              "arcsec\t \t \t \tdeg\tdeg\t \n"
              "----\t--------\t------------------------------\t-\t---------\t---------\t------------------------------\n"
              "2.94\t  238721\tKT Eri                        \t0\t 71.97583\t-10.17861\tNR                            \n\n")
VIZIER_EMPTY = (VIZIER_HEAD + "#RESOURCE=yCat_7294\n#Name: VII/294\n#Title: The Million Quasars (Milliquas) catalogue, version 8\n"
                "#Table\tVII_294_catalog:\n#Name: VII/294/catalog\n#Title: The catalogue (v8), 30-Jul-2023\n"
                "#Column\t_r\t(F5.3)\tDistance from center\t[ucd=pos.angDistance]\n\n")
VIZIER_ASSEF = (VIZIER_HEAD + "#RESOURCE=yCat_22340023\n#Name: J/ApJS/234/23\n#Title: The WISE AGN candidates catalogs (Assef+, 2018)\n"
                "#Table\tJ_ApJS_234_23_r90cat:\n#Name: J/ApJS/234/23/r90cat\n#Title: R90 final AGN candidates catalog (table 1)\n"
                "#Column\t_r\t(F5.3)\tDistance\t[ucd=pos.angDistance]\n"
                "_r\tWISEA\tRAJ2000\tDEJ2000\n \t \t \t \n-----\t-------------------\t-----------\t-----------\n"
                "0.125\tJ110629.07-443500.9\t166.6211479\t-44.5836061\n\n"
                "#Table\tJ_ApJS_234_23_c75cat:\n#Name: J/ApJS/234/23/c75cat\n#Title: C75 final AGN candidates catalog (table 2)\n"
                "#Column\t_r\t(F5.3)\tDistance\t[ucd=pos.angDistance]\n"
                "_r\tWISEA\tRAJ2000\tDEJ2000\n \t \t \t \n-----\t-------------------\t-----------\t-----------\n"
                "0.125\tJ110629.07-443500.9\t166.6211479\t-44.5836061\n\n"
                "#Table\tJ_ApJS_234_23_r90ex:\n#Name: J/ApJS/234/23/r90ex\n#Title: R90 catalog of extended sources (table 7)\n"
                "#Column\t_r\t(F5.3)\tDistance\t[ucd=pos.angDistance]\n\n")
VIZIER_ERROR = VIZIER_HEAD + "#INFO\tError=Table or Catalog not found: J/ApJS/221/12\t\n"


def test_the_catalogues_are_read_as_they_answered_and_each_has_its_own_status(monkeypatch):
    """The answers of 2026-11-05 (cut to the columns used): a VizieR table with a row, one without, one catalogue with
    several tables, an error document, and IRSA's CSV."""
    sent = []

    def fake(method, url, **kw):
        sent.append((method, url, kw))
        if url == librarian.IRSA_TAP:
            return Resp("designation,ra,dec,vartype\nVarWISE J110629.07-443500.9,166.62115,-44.58360,agn\n")
        source = kw["params"]["-source"]
        return Resp({"B/vsx/vsx": VIZIER_VSX, "VII/294": VIZIER_EMPTY, "J/ApJS/234/23": VIZIER_ASSEF,
                     "J/ApJS/221/12": VIZIER_ERROR}[source])

    monkeypatch.setattr(librarian, "request", fake)
    got = {c["key"]: c for c in librarian.catalogues(166.6211, -44.5836, 5.0)}
    assert list(got) == ["vsx", "varwise", "milliquas", "secrest2015", "assef2018"]
    assert {k: c["status"] for k, c in got.items()} == {"vsx": "ok", "varwise": "ok", "milliquas": "empty",
                                                        "secrest2015": "unavailable", "assef2018": "ok"}
    assert got["vsx"]["hits"] == [VSX_HIT] and got["vsx"]["kind"] == "variable" and got["vsx"]["bibcode"] == "2006SASS...25...47W"
    assert got["varwise"]["hits"] == [{**VARWISE_HIT, "sep_arcsec": got["varwise"]["hits"][0]["sep_arcsec"]}]
    assert got["varwise"]["hits"][0]["sep_arcsec"] < 0.2
    assert got["milliquas"]["hits"] == [] and got["milliquas"]["notes"] == []
    assert got["secrest2015"]["hits"] == [] and got["secrest2015"]["notes"] == ["VizieR: Table or Catalog not found: J/ApJS/221/12"]
    assert [h["table"] for h in got["assef2018"]["hits"]] == ["J/ApJS/234/23/r90cat", "J/ApJS/234/23/c75cat"]
    assert got["assef2018"]["hits"][0] == {**ASSEF_HIT, "sep_arcsec": 0.12} or got["assef2018"]["hits"][0] == {**ASSEF_HIT, "sep_arcsec": 0.13}

    vizier = [(m, u, k) for m, u, k in sent if u != librarian.IRSA_TAP]
    assert all((m, u) == ("GET", "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv") for m, u, k in vizier) and len(vizier) == 4
    assert vizier[0][2]["params"] == {"-source": "B/vsx/vsx", "-c": "166.6211000 -44.5836000", "-c.rs": "5", "-out.max": "50",
                                      "-out.add": "_r"}
    (m, u, k), = [x for x in sent if x[1] == librarian.IRSA_TAP]
    assert (m, u) == ("POST", "https://irsa.ipac.caltech.edu/TAP/sync") and k["timeout"] == 120.0
    assert k["data"]["FORMAT"] == "csv" and k["data"]["QUERY"] == (
        "SELECT designation, ra, dec, vartype FROM varwiseext WHERE CONTAINS(POINT('ICRS',ra,dec),"
        "CIRCLE('ICRS',166.6211000,-44.5836000,0.0013889))=1")

    # a service that is down, or answers with something that is not a table, is unavailable: never "no entry"
    def down(method, url, **kw):
        if url == librarian.IRSA_TAP:
            raise RuntimeError("irsa.ipac.caltech.edu unavailable after 2 attempts")
        return Resp("<html>Service temporarily unavailable</html>")
    monkeypatch.setattr(librarian, "request", down)
    got = librarian.catalogues(166.6211, -44.5836)
    assert [c["status"] for c in got] == ["unavailable"] * 5 and "unavailable after 2 attempts" in got[1]["notes"][0]
    assert "not a VizieR table" in got[0]["notes"][0]


# ----------------------------------------------------------------------------- merging and topics
def test_papers_are_merged_by_bibcode_across_services(monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path)
    pa = prior_art(RA, DEC)
    assert pa["n_papers"] == 5  # 5 from SIMBAD and 3 from ADS, the 3 among the 5
    by = {p["bibcode"]: p for p in pa["topical_papers"]}
    assert by[WANG]["sources"] == ["simbad", "ads"] and by["2023PASP..135c4101G"]["sources"] == ["simbad"]
    assert by[WANG]["year"] == 2018 and by[WANG]["topics"] == ["transient", "infrared_excess"]
    assert by[WANG]["title"].startswith("Long-term decline of the mid-infrared emission of normal galaxies")

    # a paper only ADS lists is kept, with the year read from its bibcode and ADS named as the source
    only_ads = {"bibcode": "2024ApJ...999..123X", "title": "A changing-look nucleus", "year": "1999"}
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=([only_ads, *ADS_PAPERS], ok()))
    pa = prior_art(RA, DEC, topics=["transient"])
    assert pa["n_papers"] == 5 and [p["bibcode"] for p in pa["topical_papers"]] == ["2024ApJ...999..123X", WANG]
    assert pa["topical_papers"][0]["sources"] == ["ads"] and pa["topical_papers"][0]["year"] == 2024
    assert pa["topical_papers"][1]["sources"] == ["ads"]  # SIMBAD's list here does not have Wang et al.


def test_topic_matching():
    assert matched_topics("A changing-look quasar") == ["transient"]
    assert matched_topics("Changing Look AGN in SDSS") == ["transient"]
    assert matched_topics("CHANGING‐LOOK active galaxies") == ["transient"]  # a typeset hyphen
    assert matched_topics("Long-term decline of the mid-infrared emission of normal galaxies: dust echo of tidal "
                          "disruption flare?") == ["transient", "infrared_excess"]
    assert matched_topics("Ten new TDEs from ZTF") == ["transient"] and matched_topics("Type Ia supernovae") == ["transient"]
    assert matched_topics("The symbiotic nova HM Sagittae") == ["transient"]
    assert matched_topics("Variability of red giants") == ["transient"]
    assert matched_topics("A deep dip in an F star") == ["dimming"] and matched_topics("Eclipsing systems") == ["dimming"]
    assert matched_topics("The vanishing of a massive star") == ["dimming"]
    assert matched_topics("A debris disk with an infrared excess") == ["infrared_excess"]
    assert matched_topics("Dusty circumstellar shells") == ["infrared_excess"]
    assert matched_topics("Orbital solution for a spectroscopic binary") == ["binary"]
    assert matched_topics("An eclipsing binary inside a dust shell") == ["dimming", "infrared_excess", "binary"]
    # whole words: a dipole is not a dip, innovative is not a nova, and a declination is not a decline
    assert matched_topics("The CMB dipole: an innovative measurement at high declination") == []
    assert matched_topics("The KPNO International Spectroscopic Survey. II. H{alpha}-selected survey list 1.") == []
    assert matched_topics("An eclipsing binary", topics=["binary"]) == ["binary"] and matched_topics("") == []
    # added after the referee's report of 2026-11-05
    for title in ("Quasi-periodic eruptions from a galactic nucleus", "A star disrupted by a black hole",
                  "The awakening of a quiescent nucleus", "Changing-state quasars in CRTS", "A kilonova candidate",
                  "Mid-infrared variations of a quasar", "A repeating fast radio burst", "X-ray bursts from a neutron star"):
        assert matched_topics(title) == ["transient"], title
    assert matched_topics("A starburst galaxy at z = 2") == []  # "burst*" is a whole word, not the end of "starburst"
    # some titles no keyword will catch; that is what the shelves and the catalogues are for
    assert matched_topics("Mrk 1018 returns to the shadows") == [] and matched_topics("Where's the flux?") == []
    # plain data: a new topic is a new entry
    assert all(isinstance(k, str) for kws in librarian.TOPICS.values() for k in kws)
    assert {"transient", "dimming", "infrared_excess", "binary"} <= set(librarian.TOPICS)


# ----------------------------------------------------------------------------- shelves
SHELF = ("# title: A test sample that no archive indexes\n"
         "# bibcode: 2099Test....1....1T\n"
         "# topics: transient, dimming\n"
         "# rows typed for this test; not a real catalogue\n"
         "name,ra,dec\n"
         "T1,216.0069,29.8412\n"
         "T2,10.0,-20.0\n")


def test_shelf_loader_hits_inside_the_radius_and_misses_outside(tmp_path):
    assert load_shelves(tmp_path) == [] and shelf_hits(RA, DEC, 5.0, tmp_path) == []  # an empty directory works
    assert load_shelves(tmp_path / "missing") == []
    (tmp_path / "test_sample.csv").write_text(SHELF)
    (tmp_path / "README.md").write_text("not a shelf")
    shelves = load_shelves(tmp_path)
    assert len(shelves) == 1 and shelves[0]["shelf"] == "test_sample" and shelves[0]["bibcode"] == "2099Test....1....1T"
    assert shelves[0]["topics"] == ["transient", "dimming"] and len(shelves[0]["sources"]) == 2
    three = RA + 3.0 / 3600 / 0.8674  # 3" east at this declination (cos 29.84 deg = 0.8674)
    hit = shelf_hits(three, DEC, 5.0, tmp_path)
    assert len(hit) == 1 and hit[0]["name"] == "T1" and abs(hit[0]["sep_arcsec"] - 3.0) < 0.02
    assert hit[0]["title"] == "A test sample that no archive indexes" and hit[0]["shelf"] == "test_sample"
    assert shelf_hits(three, DEC, 2.0, tmp_path) == []                   # 3" away, 2" radius
    assert shelf_hits(RA, DEC + 6.0 / 3600, 5.0, tmp_path) == []         # 6" north
    assert shelf_hits(10.0, -20.0, 5.0, tmp_path)[0]["name"] == "T2"
    (tmp_path / "wraps.csv").write_text("# title: Across RA zero\n# bibcode: 2099Test....1....2T\nname,ra,dec\nW,359.9999,0.0\n")
    assert [h["name"] for h in shelf_hits(0.0002, 0.0, 5.0, tmp_path)] == ["W"]  # 1.08" apart across RA = 0


def test_a_broken_shelf_raises_and_the_shipped_shelves_load(tmp_path):
    (tmp_path / "hours.csv").write_text("# title: t\n# bibcode: b\nname,ra,dec\nX,14:24:01.6,+29:50:28\n")
    with pytest.raises(ValueError, match="hours.csv, row 1"):
        load_shelves(tmp_path)
    (tmp_path / "hours.csv").write_text("name,ra,dec\nX,216.0,29.8\n")
    with pytest.raises(ValueError, match="bibcode"):
        load_shelves(tmp_path)
    (tmp_path / "hours.csv").write_text("# title: t\n# bibcode: b\nname,ra,dec\nX,216.0,129.8\n")
    with pytest.raises(ValueError, match="not degrees"):
        load_shelves(tmp_path)
    # a shelf with no row answers "not in this paper" for every position: it does not load
    for empty in ("# title: t\n# bibcode: b\nname,ra,dec\n", "# title: t\n# bibcode: b\n", "# title: t\n# bibcode: b\n\n# only comments\n"):
        (tmp_path / "hours.csv").write_text(empty)
        with pytest.raises(ValueError, match="hours.csv: no rows"):
            load_shelves(tmp_path)
        with pytest.raises(ValueError, match="no rows"):
            shelf_hits(RA, DEC, 5.0, tmp_path)
    shipped = {s["shelf"]: s for s in load_shelves()}  # whatever is in src/oddsky/shelves must parse
    for s in shipped.values():
        assert s["title"] and s["bibcode"] and s["sources"]
    assert {"graham2020_csq", "jiang2021_mirong", "macleod2019_clq", "wang2018_mir_decline"} <= set(shipped)
    assert len(shipped["wang2018_mir_decline"]["sources"]) == 14 and len(shipped["jiang2021_mirong"]["sources"]) == 137


def test_the_graham_shelf_holds_table_2_and_not_the_phantoms_or_the_literature_table():
    """The first build took every table of J/MNRAS/491/4925: three positions that exist nowhere (sign and typing errors in
    table B1's names) and the 61 changing-look quasars of table A1, which are other people's."""
    g = {s["shelf"]: s for s in load_shelves()}["graham2020_csq"]
    assert len(g["sources"]) == 111 and all(x["name"].startswith("SDSS J") for x in g["sources"])  # the paper's own names
    for ra, dec in ((41.39, 0.1292222), (44.0791667, 0.7502778), (169.8766667, 31.4046389)):  # the phantoms of table B1
        assert not [h for h in shelf_hits(ra, dec, 30.0) if h["shelf"] == "graham2020_csq"]
    for ra, dec, name in ((41.39, -0.1292222, "SDSS J024533.6-000745.2"), (44.0791667, -0.7502778, "SDSS J025619.0-004501.0"),
                          (169.8766667, 22.4471667, "SDSS J111930.4+222649.8")):  # the three as table 2 has them
        assert [h["name"] for h in shelf_hits(ra, dec, 2.0) if h["shelf"] == "graham2020_csq"] == [name]
    # table A1's first row, SDSS J000904.5-103428 (a literature CLQ), is not Graham's: MacLeod et al. 2019 has it
    assert [h["shelf"] for h in shelf_hits(2.26875, -10.5744444, 5.0)] == ["macleod2019_clq"]


def test_a_shelf_hit_is_studied_even_with_no_paper_in_the_archives(monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED)
    shelves = tmp_path / "shelves"
    shelves.mkdir()
    (shelves / "test_sample.csv").write_text(SHELF)
    monkeypatch.setattr(librarian, "SHELVES_DIR", shelves)
    pa = prior_art(RA, DEC)
    assert pa["verdict"] == "studied" and pa["n_papers"] == 0 and pa["shelf_hits"][0]["bibcode"] == "2099Test....1....1T"
    assert pa["summary"] == ("Studied: this position is in a published sample on the shelves as T1: 2099Test....1....1T, "
                             "\"A test sample that no archive indexes\".")
    assert prior_art(RA, DEC + 0.01)["verdict"] == "unlisted"


# ----------------------------------------------------------------------------- the Skeptic, fetch and the tool
def _check(store, pa):
    ctx = store.context()
    ctx.pop("prior_art", None)
    if pa is not None:
        ctx["prior_art"] = pa
    store.write_context(ctx)
    c = [x for x in skeptic.run(store, write=False)["checks"] if x["id"] == "prior_art"]
    assert len(c) == 1
    return c[0]


def test_skeptic_skips_until_the_literature_is_fetched(dusty_case):
    c = _check(dusty_case, None)
    assert c["status"] == "skip" and "oddsky fetch <case> --surveys librarian" in c["finding"]


def test_skeptic_warns_when_studied_and_lists_the_newest_titles(dusty_case, monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path)
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["finding"].startswith("2 of 5 papers on 2MASX J14240163+2950285 match the topics")
    assert '2018MNRAS.477.2943W "Long-term decline of the mid-infrared emission of normal galaxies' in c["finding"]
    assert '2023PASP..135c4101G "A Census of Archival X-Ray Spectra' in c["finding"]
    assert c["finding"].endswith("These must be read before anything here is called new.")
    assert c["numbers"]["verdict"] == "studied" and c["numbers"]["complete"] is True and c["numbers"]["n_topical"] == 2
    assert c["numbers"]["newest"] == ["2023PASP..135c4101G", WANG]

    # only the newest three are listed, with the full count
    many = [{"bibcode": f"{y}ApJ...{y}....1F", "title": f"A flare in {y}"} for y in range(2010, 2020)]
    patch(monkeypatch, tmp_path, simbad=sim(many), ads=([], ok()))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["finding"].startswith("10 of 10 papers") and c["numbers"]["newest"] == [f"{y}ApJ...{y}....1F" for y in (2019, 2018, 2017)]
    assert "A flare in 2017" in c["finding"] and "A flare in 2016" not in c["finding"]


def test_skeptic_passes_when_catalogued_or_unlisted(dusty_case, monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok()))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "pass" and c["numbers"]["verdict"] == "catalogued"
    assert c["finding"] == ("3 papers list 2MASX J14240163+2950285; no title matches the topics (transient, dimming, "
                            "infrared_excess, binary) and no shelf holds it")
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED)
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "pass" and c["numbers"]["verdict"] == "unlisted"
    assert c["finding"] == "no SIMBAD object, no NED object and no shelf entry within 5\""


def test_skeptic_never_presents_an_incomplete_verdict_as_final(dusty_case, monkeypatch, tmp_path):
    down = ([], ok(status="unavailable", notes=["no ADS token"]))
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=down)
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["verdict"] == "catalogued" and c["numbers"]["complete"] is False
    assert c["finding"].startswith("not final: ADS could not be queried.") and c["numbers"]["unavailable"] == ["ADS"]
    assert "Re-run `oddsky fetch <case> --surveys librarian`" in c["finding"]

    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NED_DOWN)
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["finding"].startswith("not final: NED and ADS could not be queried.")
    assert "no SIMBAD object" not in c["finding"]  # what did not answer is not listed as having nothing

    patch(monkeypatch, tmp_path, ads=down)  # studied on SIMBAD's list alone: still a warning, and still says ADS failed
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["verdict"] == "studied" and c["numbers"]["complete"] is False
    assert c["finding"].endswith("The list is incomplete: ADS could not be queried.")


def test_skeptic_passes_mentioned_and_says_what_it_means(dusty_case, monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=sim([*QUIET, BIG, UGC], main_id="NGC 821"),
          ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok()))
    c = _check(dusty_case, prior_art(RA, DEC, topics="transient"))
    assert c["status"] == "pass" and c["numbers"]["verdict"] == "mentioned" and c["numbers"]["complete"] is True
    assert (c["numbers"]["n_topical"], c["numbers"]["n_about"]) == (2, 0)
    assert c["finding"] == ("2 of 5 papers on NGC 821 match the topics (transient), but only in lists of more than 500 objects: "
                            "it is in their tables, and no paper is about it; newest: 2019ApJ...887..169F \"A measurement of "
                            "the supernova rate in 4000 galaxies\"; 1973UGC...C...0000N \"Uppsala General Catalogue of "
                            "Galaxies. Acta Universitatis Upsaliensis, Nova Regiae Societatis\"")


def test_skeptic_reports_object_types_catalogues_and_a_list_cut_short(dusty_case, monkeypatch, tmp_path):
    empty = ([], ok(status="empty"))
    # a variable catalogue and a transient type are reasons to read, like a paper: a warning
    patch(monkeypatch, tmp_path, simbad=sim([], main_id="V* KT Eri", otype="No*"), ned=NO_NED, ads=empty,
          catalogues=cats(vsx=[VSX_HIT]))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["otypes"] == ["No*"] and c["numbers"]["catalogues"] == ["vsx"]
    assert c["finding"] == ("SIMBAD has a transient-type object here: V* KT Eri (No*, nova). catalogued as a variable: VSX has "
                            "KT Eri (type NR), 2006SASS...25...47W. These must be read before anything here is called new.")
    # an AGN catalogue is reported and stays a pass
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=ned_is(ANON), ads=empty,
          catalogues=cats(secrest2015=[SECREST_HIT], assef2018=[ASSEF_HIT]))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "pass" and c["numbers"]["verdict"] == "catalogued"
    assert c["finding"].endswith("no shelf holds it; listed as an AGN or AGN candidate in Secrest et al. 2015 and Assef et al. 2018")
    # a catalogue that did not answer, or an ADS list cut short: not final, by name
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=empty, catalogues=cats(varwise="unavailable"))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["finding"].startswith("not final: VarWISE could not be queried.")
    assert c["numbers"]["unavailable"] == ["VarWISE"]
    cut = ok(rows_raw=1373, rows_kept=1000)
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], cut))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["complete"] is False and c["numbers"]["unavailable"] == []
    assert c["finding"].startswith("not final: ADS holds 1373 papers and only the newest 1000 were read. From the sources")
    # an answer stored before the catalogues existed is still read
    old = {"verdict": "catalogued", "complete": True, "n_papers": 3, "n_topical": 0, "topical_papers": [], "shelf_hits": [],
           "topics": ["transient"], "radius_arcsec": 5.0, "simbad": {"main_id": "X"}, "ned": None,
           "sources": {k: {"status": "ok", "notes": []} for k in ("simbad", "ned", "ads")}}
    c = _check(dusty_case, old)
    assert c["status"] == "pass" and c["finding"].startswith("3 papers list X; no title matches")


def test_the_command_prints_the_summary_the_sources_and_the_catalogues(monkeypatch, tmp_path):
    from typer.testing import CliRunner

    from oddsky.cli import app

    asked = patch(monkeypatch, tmp_path, simbad=sim([*SIMBAD_PAPERS, BIG]),
                  catalogues=cats(varwise=[VARWISE_HIT], secrest2015=[SECREST_HIT], vsx="unavailable"))
    r = CliRunner().invoke(app, ["librarian", str(RA), str(DEC), "--topic", "transient", "--epoch", "2010.5"])
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    assert lines[0].startswith("Not final (VSX could not be queried); so far studied: 2 of 6 papers on") and asked.epochs == [2010.5]
    assert "  SIMBAD: 2MASX J14240163+2950285 (EmG), 0.1\" away at 2010.5" in lines
    assert "  ADS:    asked about 2MASX J14240163+2950285, WISEA J142401.66+295028.4" in lines
    assert ("  VarWISE: VarWISE J110629.07-443500.9 (type agn), 0.1\" away, 2026ApJS..284...41P [published as variable]") in lines
    assert ("  Secrest et al. 2015: J110629.07-443500.9, 0.1\" away, 2015ApJS..221...12S [listed as an AGN or AGN candidate; "
            "does not change the verdict]") in lines
    assert "  VSX could not be queried: timeout" in lines and "  no entry in: Milliquas, Assef et al. 2018" in lines
    assert "  6 paper(s), 3 on the topics (transient), 1 of them in lists of more than 500 objects, newest first:" in lines
    assert any(ln.endswith("A measurement of the supernova rate in 4000 galaxies  [a list of 4361 objects]") for ln in lines)
    # a negative declination is an argument, with or without "--"
    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=NO_NED)
    r = CliRunner().invoke(app, ["librarian", "--", "106.2231", "-42.8842"])
    assert r.exit_code == 0 and r.output.splitlines()[0] == "Unlisted: no SIMBAD object, no NED object and no shelf entry within 5\"."
    assert "  ADS:    not asked (no object name to look up)" in r.output.splitlines()


def test_fetch_stores_the_answer_and_keeps_a_complete_one_over_an_incomplete_one(dusty_case, monkeypatch, tmp_path):
    from oddsky import fetch as fetch_mod

    assert "librarian" in fetch_mod.SURVEYS
    asked = []
    patch(monkeypatch, tmp_path)
    real = librarian.prior_art
    monkeypatch.setattr(fetch_mod.librarian, "prior_art", lambda ra, dec: (asked.append((ra, dec)), real(ra, dec))[1])
    rep = fetch_mod.fetch(dusty_case, ("librarian",))
    assert asked == [(10.0, -20.0)]  # the case position
    assert rep["librarian"] == {"status": "ok", "rows": 5, "verdict": "studied"}
    pa = dusty_case.context()["prior_art"]  # read back from disk: the key survives fetch()'s final save
    assert pa["verdict"] == "studied" and pa["complete"] is True and pa["topical_papers"][1]["bibcode"] == WANG
    assert dusty_case.provenance()["librarian"]["status"] == "ok"
    assert [c["status"] for c in skeptic.run(dusty_case, write=False)["checks"] if c["id"] == "prior_art"] == ["warn"]

    # a re-check with ADS down does not replace the complete answer, and the report says it was incomplete
    patch(monkeypatch, tmp_path, simbad=sim(QUIET), ads=([], ok(status="unavailable", notes=["no ADS token"])))
    rep = fetch_mod.fetch(dusty_case, ("librarian",))
    assert rep["librarian"] == {"status": "unavailable", "rows": 3, "verdict": "catalogued", "unavailable": ["ADS"]}
    assert dusty_case.context()["prior_art"]["verdict"] == "studied"
    assert "ads: unavailable (no ADS token)" in dusty_case.provenance()["librarian"]["notes"]

    # a first check that is incomplete is stored as incomplete
    ctx = dusty_case.context()
    del ctx["prior_art"]
    dusty_case.write_context(ctx)
    fetch_mod.fetch(dusty_case, ("librarian",))
    assert dusty_case.context()["prior_art"]["complete"] is False

    # other surveys do not ask the Librarian
    asked.clear()
    monkeypatch.setattr(fetch_mod.allwise, "catalog", lambda ra, dec, r: (None, Provenance(archive="fake", status="empty")))
    assert "librarian" not in fetch_mod.fetch(dusty_case, ("allwise",)) and asked == []


def test_the_tool_works_on_a_position_or_a_case_and_is_ledgered_with_a_case(dusty_case, monkeypatch, tmp_path):
    from oddsky.tools import Toolbox, available

    patch(monkeypatch, tmp_path)
    assert "prior_art" in available("open") and "prior_art" not in available("blind")
    tb = Toolbox(author="test")
    r = tb.prior_art(ra=RA, dec=DEC)
    assert r["verdict"] == "studied" and "call_id" not in r and dusty_case.ledger() == []  # no case: nothing to ledger
    r = tb.prior_art(case="OS-0001", topics=["transient"], max_papers=1)
    assert r["call_id"] == "K1" and (r["ra"], r["dec"]) == (10.0, -20.0)  # the case's own position
    assert r["n_topical"] == 2 and len(r["topical_papers"]) == 1
    led = dusty_case.ledger()
    assert led[0]["tool"] == "prior_art" and led[0]["args"]["topics"] == ["transient"] and "case" not in led[0]["args"]
    with pytest.raises(ValueError, match="ra and dec"):
        tb.prior_art()
    with pytest.raises(PermissionError):
        Toolbox(mode="blind", blind_root=dusty_case.path).prior_art(ra=RA, dec=DEC)

"""The Librarian: is it new? Offline: the three services are replaced by what they returned on 2026-11-05 for
RA 216.0069, Dec 29.8412, the galaxy H-0017 called its "best candidate" (object 12 of Wang et al. 2018)."""
import pytest

from oddsky import librarian, skeptic
from oddsky.data.provenance import Provenance
from oddsky.librarian import load_shelves, matched_topics, prior_art, shelf_hits

RA, DEC = 216.0069, 29.8412
WANG = "2018MNRAS.477.2943W"
SIMBAD_OBJ = {"main_id": "2MASX J14240163+2950285", "otype": "EmG", "ra": 216.00692860053996, "dec": 29.84119873223,
              "sep_arcsec": 0.09}
SIMBAD_PAPERS = [
    {"bibcode": "2023PASP..135c4101G", "title": "A Census of Archival X-Ray Spectra for Modeling Tidal Disruption Events."},
    {"bibcode": "2005AJ....130..496J",
     "title": "Spectroscopy of KISS emission-line galaxy candidates. III. A second set of MDM observations."},
    {"bibcode": "2001AJ....121...66S",
     "title": "The KPNO International Spectroscopic Survey. II. H{alpha}-selected survey list 1."},
    {"bibcode": "2014ApJ...788...45T", "title": "Luminosity and redshift dependence of the covering factor of active "
                                                "galactic nuclei viewed with WISE and Sloan Digital Sky Survey."},
    {"bibcode": WANG,
     "title": "Long-term decline of the mid-infrared emission of normal galaxies: dust echo of tidal disruption flare?"},
]
NED_OBJ = {"prefname": "WISEA J142401.66+295028.4", "type": "G", "z": 0.085530415, "ra": 216.0069291, "dec": 29.8412329,
           "sep_arcsec": 0.03, "n_objects": 1}
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


def patch(monkeypatch, tmp_path, simbad=None, ned=None, ads=None):
    """Replace the three services (and point the shelves at an empty directory). Each argument is what the service
    function returns; the default is the real answer for the H-0017 galaxy."""
    simbad = simbad or ({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": [dict(p) for p in SIMBAD_PAPERS]}, ok())
    ned = ned or (dict(NED_OBJ), ok())
    ads = ads or ([dict(p) for p in ADS_PAPERS], ok())
    asked = []
    monkeypatch.setattr(librarian, "simbad", lambda ra, dec, radius_arcsec=5.0: simbad)
    monkeypatch.setattr(librarian, "ned", lambda ra, dec, radius_arcsec=5.0: ned)
    monkeypatch.setattr(librarian, "ads_papers", lambda name: (asked.append(name), ads)[1])
    monkeypatch.setattr(librarian, "SHELVES_DIR", tmp_path / "no-shelves")
    return asked


NO_SIMBAD = ({"object": None, "n_objects": 0, "papers": []}, ok(status="empty"))
NO_NED = (None, ok(status="empty"))


# ----------------------------------------------------------------------------- verdicts
def test_studied_the_h0017_best_candidate_was_object_12_of_wang_2018(monkeypatch, tmp_path):
    asked = patch(monkeypatch, tmp_path)
    pa = prior_art(RA, DEC)
    assert asked == ["WISEA J142401.66+295028.4"]  # ADS is asked about the NED object
    assert pa["verdict"] == "studied" and pa["complete"] is True
    assert pa["simbad"]["main_id"] == "2MASX J14240163+2950285" and pa["simbad"]["otype"] == "EmG"
    assert pa["ned"] == {"prefname": "WISEA J142401.66+295028.4", "type": "G", "z": 0.085530415, "sep_arcsec": 0.03,
                         "n_objects": 1}
    assert pa["n_papers"] == 5 and pa["n_topical"] == 2
    assert [p["bibcode"] for p in pa["topical_papers"]] == ["2023PASP..135c4101G", WANG]  # newest first
    assert pa["topics"] == ["transient", "dimming", "infrared_excess", "binary"]  # None means every topic
    assert {k: v["status"] for k, v in pa["sources"].items()} == {"simbad": "ok", "ned": "ok", "ads": "ok"}
    assert pa["shelf_hits"] == [] and (pa["ra"], pa["dec"], pa["radius_arcsec"]) == (RA, DEC, 5.0)
    assert pa["summary"] == ("Studied: 2 of 5 papers on 2MASX J14240163+2950285 match the topics (transient, dimming, "
                             "infrared_excess, binary); the newest is 2023PASP..135c4101G, \"A Census of Archival X-Ray "
                             "Spectra for Modeling Tidal Disruption Events\".")


def test_catalogued_an_object_with_papers_and_none_on_the_topic(monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()),
          ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok()))
    pa = prior_art(RA, DEC)
    assert pa["verdict"] == "catalogued" and pa["complete"] is True and pa["n_papers"] == 3 and pa["topical_papers"] == []
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
    assert pa["simbad"] is None and pa["ned"] is None and asked == []  # no NED object: nothing to ask ADS
    assert pa["sources"]["ads"]["status"] == "empty" and "no NED object" in pa["sources"]["ads"]["notes"][0]
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
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()), ads=down)
    pa = prior_art(RA, DEC)
    assert pa["complete"] is False and pa["verdict"] == "catalogued" and pa["sources"]["ads"]["status"] == "unavailable"
    assert pa["summary"].startswith("Not final (ADS could not be queried); so far catalogued: ")

    # SIMBAD down: NED and ADS still find the paper, and the answer still says SIMBAD was not asked
    patch(monkeypatch, tmp_path, simbad=({"object": None, "n_objects": 0, "papers": []},
                                         ok(status="unavailable", notes=["simbad.harvard.edu unavailable after 2 attempts"])))
    pa = prior_art(RA, DEC)
    assert pa["complete"] is False and pa["verdict"] == "studied" and pa["simbad"] is None
    assert pa["summary"].startswith("Not final (SIMBAD could not be queried); so far studied: 1 of 3 papers on "
                                    "WISEA J142401.66+295028.4 matches")

    # NED down: ADS could not be asked either, and nothing found is not "unlisted" as a fact
    asked = patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=(None, ok(status="unavailable", notes=["timeout"])))
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
        text = "main_id,otype,ra,dec\n"
    monkeypatch.setattr(librarian, "request", lambda *a, **k: Header)
    out, prov = librarian.simbad(RA, DEC)
    assert out == {"object": None, "n_objects": 0, "papers": []} and prov.status == "empty"


def test_the_services_are_read_as_they_answered_on_2026_11_05(monkeypatch):
    """The CSV each TAP service returned for RA 216.0069, Dec 29.8412, and the query shapes sent."""
    sent = []

    class Resp:
        def __init__(self, text):
            self.text = text

    def fake(method, url, **kw):
        q = (kw.get("data") or kw.get("params"))["QUERY"]
        sent.append((method, url, q))
        if "NEDTAP" in q:
            return Resp("prefname,ra,dec,uncmaja,uncmina,uncposa,gallon,gallat,pos_bibcode,prefphytype,z,zunc,z_bibcode,zflag,"
                        "n_crosref,n_notes,n_gphot,n_posd,n_zdf,n_ddf,n_dist,n_class,n_images,n_spectra,objid,type_key\n"
                        '"WISEA J142401.66+295028.4",216.0069291,29.8412329,0.09075,0.0895,90.0,46.0039122899956,'
                        '69.5098133411628,"2013wise.rept....1C","G",0.085530415,1.05051395E-5,"2016SDSSD.C...0000:","SLS",'
                        "29,0,58,11,9,6,0,0,1,1,2624218,55\n")
        if "has_ref" in q:
            return Resp("bibcode,title\n" + "".join(f'"{p["bibcode"]}","{p["title"]}"\n' for p in SIMBAD_PAPERS))
        return Resp('main_id,otype,ra,dec\n"2MASX J14240163+2950285","EmG",216.00692860053996,29.84119873223\n')

    monkeypatch.setattr(librarian, "request", fake)
    out, prov = librarian.simbad(RA, DEC)
    assert prov.status == "ok" and prov.rows_kept == 5 and out["n_objects"] == 1
    assert out["object"]["main_id"] == "2MASX J14240163+2950285" and out["object"]["otype"] == "EmG"
    assert out["object"]["sep_arcsec"] < 0.2 and out["papers"] == SIMBAD_PAPERS
    obj, prov = librarian.ned(RA, DEC)
    assert prov.status == "ok" and obj["prefname"] == "WISEA J142401.66+295028.4" and obj["type"] == "G"
    assert abs(obj["z"] - 0.0855) < 1e-4 and obj["sep_arcsec"] < 0.2
    (m1, u1, q1), (m2, u2, q2), (m3, u3, q3) = sent
    cone = "CIRCLE('ICRS',216.0069000,29.8412000,0.0013889))=1"
    assert (m1, u1) == (m2, u2) == ("POST", "https://simbad.harvard.edu/simbad/sim-tap/sync")
    assert q1 == f"SELECT main_id, otype, ra, dec FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),{cone}"
    assert q2 == ("SELECT bibcode, title FROM basic JOIN has_ref ON oidref=oid JOIN ref ON oidbib=oidbibref "
                  f"WHERE CONTAINS(POINT('ICRS',ra,dec),{cone}")
    assert "ORDER BY" not in q1 + q2 and " AS " not in q1 + q2  # this SIMBAD mirror rejects both
    assert (m3, u3) == ("GET", "https://ned.ipac.caltech.edu/tap/sync")
    assert q3 == ("SELECT * FROM NEDTAP.objdir WHERE CONTAINS(POINT('J2000',ra,dec),"
                  "CIRCLE('J2000',216.0069000,29.8412000,0.0013889))=1")


def test_ads_is_asked_with_the_ned_name_and_the_token_never_leaves_the_header(monkeypatch):
    monkeypatch.setenv("ADS_TOKEN", "s3cret-token")
    sent = []

    class Resp:
        def __init__(self, payload):
            self._p = payload

        def json(self):
            return self._p

    def fake(method, url, **kw):
        sent.append((method, url, kw))
        if url.endswith("/objects/query"):
            return Resp({"query": '((=abs:"WISEA J142401.66+295028.4" OR nedid:"WISEA_J142401.66+295028.4") database:astronomy)'})
        return Resp({"response": {"numFound": 3, "docs": [dict(p, title=[p["title"]]) for p in ADS_PAPERS]}})

    monkeypatch.setattr(librarian, "request", fake)
    papers, prov = librarian.ads_papers("WISEA J142401.66+295028.4")
    assert prov.status == "ok" and papers == ADS_PAPERS  # ADS gives the title as a list; the first is kept
    (m1, u1, k1), (m2, u2, k2) = sent
    assert (m1, u1) == ("POST", "https://api.adsabs.harvard.edu/v1/objects/query")
    assert k1["json"] == {"query": ['object:"WISEA J142401.66+295028.4"']}
    assert (m2, u2) == ("GET", "https://api.adsabs.harvard.edu/v1/search/query")
    assert k2["params"] == {"q": '((=abs:"WISEA J142401.66+295028.4" OR nedid:"WISEA_J142401.66+295028.4") database:astronomy)',
                            "fl": "bibcode,title,year", "rows": 200}
    assert k1["headers"] == k2["headers"] == {"Authorization": "Bearer s3cret-token"}
    assert "s3cret" not in prov.model_dump_json()

    def leaky(method, url, **kw):
        raise RuntimeError("401 for token s3cret-token")
    monkeypatch.setattr(librarian, "request", leaky)
    papers, prov = librarian.ads_papers("WISEA J142401.66+295028.4")
    assert prov.status == "unavailable" and "s3cret" not in prov.notes[0] and "<token>" in prov.notes[0]

    monkeypatch.setattr(librarian, "request", lambda m, u, **k: Resp({"query": "q"} if u.endswith("/objects/query") else
                                                                    {"response": {"numFound": 0, "docs": []}}))
    assert librarian.ads_papers("nothing here")[1].status == "empty"


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
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()),
          ads=([only_ads, *ADS_PAPERS], ok()))
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
    for s in load_shelves():  # whatever is in src/oddsky/shelves (possibly nothing) must parse
        assert s["title"] and s["bibcode"] and s["sources"]


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
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": many}, ok()), ads=([], ok()))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["finding"].startswith("10 of 10 papers") and c["numbers"]["newest"] == [f"{y}ApJ...{y}....1F" for y in (2019, 2018, 2017)]
    assert "A flare in 2017" in c["finding"] and "A flare in 2016" not in c["finding"]


def test_skeptic_passes_when_catalogued_or_unlisted(dusty_case, monkeypatch, tmp_path):
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()),
          ads=([p for p in ADS_PAPERS if p["bibcode"] != WANG], ok()))
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
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()), ads=down)
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["verdict"] == "catalogued" and c["numbers"]["complete"] is False
    assert c["finding"].startswith("not final: ADS could not be queried.") and c["numbers"]["unavailable"] == ["ADS"]
    assert "Re-run `oddsky fetch <case> --surveys librarian`" in c["finding"]

    patch(monkeypatch, tmp_path, simbad=NO_SIMBAD, ned=(None, ok(status="unavailable", notes=["timeout"])))
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["finding"].startswith("not final: NED and ADS could not be queried.")
    assert "no SIMBAD object" not in c["finding"]  # what did not answer is not listed as having nothing

    patch(monkeypatch, tmp_path, ads=down)  # studied on SIMBAD's list alone: still a warning, and still says ADS failed
    c = _check(dusty_case, prior_art(RA, DEC))
    assert c["status"] == "warn" and c["numbers"]["verdict"] == "studied" and c["numbers"]["complete"] is False
    assert c["finding"].endswith("The list is incomplete: ADS could not be queried.")


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
    patch(monkeypatch, tmp_path, simbad=({"object": dict(SIMBAD_OBJ), "n_objects": 1, "papers": QUIET}, ok()),
          ads=([], ok(status="unavailable", notes=["no ADS token"])))
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

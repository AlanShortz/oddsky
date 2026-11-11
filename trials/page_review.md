# Referee review of the Trials page text (trials/page.json)

document-sha256: 7a4a47c32ab931673127918fd858b3ef1a2f0937a26e91c69947659f4d6e734b

Three passes on 2026-11-10 by independent reviewers who were given the files, not the author's conclusions.

## Pass 1 (first draft): must fix
The first draft was not publishable. What the reviewer found, and what changed:

1. "In no paper / nobody has written about" was false for at least four of the eight Trial 002 stars
   (OS-0010 is NSV 1302, a decades-old suspected variable; OS-0015 is in two variable-candidate catalogues;
   OS-0013 is in VarWISE; OS-0012 is a VSX 'VAR'). The trial was retitled and the lede now says several are
   catalogued and that we know of no paper describing what they do.
2. The answer key for the scored stars was written with Opus 5.5, one of the three models under test, and the
   draft did not say so. It now does, and says agreement with the key is consistency, not confirmation.
3. "The four blind packets" contradicted "five that have an answer". Corrected to five scored packets.
4. "Forecasts came true" was used as the skill measure; it ignores stated probabilities and the prompt asks for
   a near-50/50 forecast per packet. The summary now leads with the Brier score.
5. Small-sample overreach: forecasts on one star are not independent; five of Fable's fifteen rest on three
   measurements; three come from the packet with the rules breach. All now stated.
6. The H03 breach was understated: the packet was redone from the start inside the repository. Now stated,
   with "we cannot verify" what was opened.
7. A run note claimed forecasts "announced before the interruption"; nothing was on record. Removed.
8-15. Same-tools wording, the tool-bug causal claim, the grader-change description (the three forecasts are
   now named; four verdicts changed, none became a hit), recognition counted in packets not stars, "its
   investigators", sealed-before-run ledes for Fable's Trial 001 run, and smaller wording points.

## Pass 2 (revised text): publishable; 11 of 15 resolved, 4 partly
Leftovers applied afterwards: README wording, "sealed before the first run", "worked on all four of those
cases", "plus checks outside it and data the investigators did not have", and the manifest description.

The three claims the receipts mark as external were checked against the ledgers:
- "about two minutes in": first call 00:09:23Z, last before the gap 00:11:12Z.
- "Two of its packets were finished": T04 ends 00:10:28Z, T02 00:11:04Z; no later entries.
- "Four verdicts changed in all": all 43 Trial 002 forecast windows recomputed against cutoffs and series
  ends. Fable H03 P1 (window opened 0.43 d before the cutoff) went from invalid to false; Haiku H04 P2 and
  Opus H04 P3 and P4 (ASAS-SN V ended at MJD 58378) went from pending to unresolvable. No Trial 001 verdict
  is affected.

## Pass 3 (this exact text): publishable as is
No false or unsupported sentence found. Noted for the record: the Trial 002 seal commit (00d4310) precedes the
first investigator call by 29 seconds; "plus checks outside it" is true of the four cases together but OS-0010
records no outside check, and the sealed answer file still calls it a "refereed conclusion", which the page
overrides with "Oddsky's own conclusion".

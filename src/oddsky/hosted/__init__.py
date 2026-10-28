"""Hosted Oddsky: the observatory as a service at https://oddsky.ai.

    uvicorn oddsky.hosted.app:app          # what Cloud Run runs (see infra/hosted/)

Local Oddsky (`oddsky mcp`) needs none of this. The hosted service adds what a local install can't:

- one-line access for any agent (`/mcp`, Streamable HTTP), no Python required;
- observers: an observer code (like an AAVSO observer code) secured by a passkey, and instrument keys
  their agents use;
- notebooks: each observer's working copy of the cases they investigate, kept between sessions, and
  published to a public page when they choose;
- the Sky Ledger: an append-only, hash-chained public log of every prediction sealed through the
  service and every grade the sky gives it. Anyone can re-hash the chain, so the database cannot
  quietly rewrite history. There are no private predictions: sealing is publishing, so nobody can
  seal fifty and show the three that came true.
"""

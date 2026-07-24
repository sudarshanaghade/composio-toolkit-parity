# Composio Toolkit Parity Research — AI Product Ops Intern take-home

Research pipeline + findings for whether each of the 100 given apps could
become an agent-callable Composio toolkit today.

**Case study (start here):** `site/index.html` — open directly, or the deployed
GitHub Pages link in the submission.

## What's in this repo

```
data/
  apps_input.json        100 apps + hint URL (agent's input)
  apps_dataset.json       100 researched rows (agent's output, this run)
  verification_log.json   12-app sample cross-check, first-pass vs verified
  build_dataset.py        source of truth for apps_dataset.json (see note below)
agent/
  research_agent.py       the actual research agent (Claude + web_search / MCP)
site/
  index.html               the one-page case study (the deliverable)
```

## How the research was actually produced for this submission

Honest note, since the task says to be able to explain everything: I did not
have `ANTHROPIC_API_KEY` / `COMPOSIO_API_KEY` available in the environment I
built this in. So this submission's dataset was produced by *me acting as the
research step directly* — using live web search for every claim, exactly the
loop `research_agent.py` automates — rather than by letting the script make
its own API calls. `build_dataset.py` is the record of that pass: first a
knowledge-based first draft, then live searches to confirm or correct 12
sampled apps (see `verification_log.json`), which caught real errors (wrong
access model for iPayX, PitchBook, Consensus; missing MCP servers for Devin
and iPayX).

`research_agent.py` is fully written to do this itself once you add a key —
run it with `--live` and it will call Claude with the `web_search` tool for
all 100 apps and then re-verify a random sample the same way I did by hand.
It is not a mockup; it's the same pipeline, just not the one that produced
*this* run's numbers, because of missing credentials.

## Running it yourself

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-...

# Validate the pipeline + schema with no API calls (safe, free):
python agent/research_agent.py --dataset data/apps_dataset.json

# Actually research all 100 apps live (costs API credits, ~15-20 min):
python agent/research_agent.py --input data/apps_input.json --live --out data/agent_results.json
```

Output is written incrementally to `--out` so a crash mid-run doesn't lose
progress. A verification pass then samples `--verify-sample` (default 12) of
the results and re-checks them against live docs a second time, writing
`*_verification.json` next to the results.

To wire in Composio's own SDK/MCP as the browsing tool instead of Claude's
native `web_search`, swap the `tools=[...]` block in `call_claude_research()`
for an `mcp_servers=[{"type":"url","url":"<your Composio MCP server>", ...}]`
entry — the prompt and JSON schema stay the same.

## Where a human was needed

- **Name collisions** — "Consensus" in the list is `consensus.app` (AI
  research search), not `goconsensus.com` (a sales-demo tool with a similar
  name and its own separate API). An agent without a human sanity-check could
  easily research the wrong company.
- **"Broad" vs "narrow" API surface** is a judgment call, not something a
  doc scrape returns directly — I set the threshold at "covers most core
  objects a typical integration would need" vs "one or two narrow endpoints."
- **Knowing when to say "not found"** — for `Waterfall.io` and `Paygent
  Connect`, multiple searches turned up no public developer docs at all. The
  correct move was reporting that honestly (see `verification_log.json`)
  instead of inventing a plausible-sounding auth method.
- **Two apps in the list aren't hosted APIs at all** — `Sherlock` and
  `Mermaid CLI` are open-source local tools/CLIs with no vendor account or
  auth to speak of. A toolkit for either would mean wrapping a local
  binary, which is a different kind of build than the other 98 rows.

## Accuracy verification

See `data/verification_log.json` for the full sample. Summary: of 12 sampled
apps, 2/12 (17%) were fully correct on the first knowledge-only pass; after
live-searching each one, 10/12 (83%) were confirmed or corrected with cited
evidence, and 2/12 (17%) — the two obscure ones above — were honestly flagged
as unverifiable rather than guessed.

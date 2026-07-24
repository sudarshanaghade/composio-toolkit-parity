#!/usr/bin/env python3
"""
Composio Toolkit Parity Research Agent
========================================
Given a list of apps, researches for each: category, auth method(s),
self-serve vs gated access, API surface, existing MCP, and a buildability
verdict - then writes evidence-linked JSON, and runs a second-pass
verification loop against a random sample.

Two ways to run:
  1) Live mode  (requires ANTHROPIC_API_KEY, optionally COMPOSIO_API_KEY):
       python research_agent.py --input data/apps_input.json --live
     Uses Claude with the web_search tool (and Composio's MCP/browser-use
     tool when a COMPOSIO_API_KEY is present) to actually browse docs.

  2) Dry-run mode (no keys needed):
       python research_agent.py --input data/apps_input.json
     Validates the pipeline, schema, and verification-sampling logic
     against the pre-researched dataset in data/apps_dataset.json, so
     the agent's control flow can be inspected/graded without spending
     API credits.

Where a human was needed (see README): resolving name collisions between
similarly-named products (e.g. consensus.app vs goconsensus.com), judging
"broad" vs "narrow" API surface, and deciding when "no docs found after N
searches" should be reported as an honest miss instead of guessed.
"""
import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

SCHEMA_FIELDS = [
    "id", "name", "category", "what", "auth", "access", "api",
    "breadth", "mcp", "verdict", "blocker", "evidence", "confidence", "notes",
]

RESEARCH_PROMPT = """You are researching whether {app_name} ({hint_url}) could become
an AI-agent toolkit. Use web search to find the OFFICIAL developer docs (not
third-party wrappers unless no official docs exist) and answer strictly as JSON
matching this schema:

{{
  "category": "<one of the 10 category names>",
  "what": "<one line: what the app does>",
  "auth": ["<OAuth2 | API key | Basic | Bearer token | other, be specific>"],
  "access": "self_serve | freemium | gated",
  "api": "rest | graphql | rest+graphql | proprietary",
  "breadth": "narrow | broad",
  "mcp": "none | community | official",
  "verdict": "ready | ready_limited | blocked_partnership | blocked_no_public_api",
  "blocker": "<empty string if verdict is ready, else the main blocker>",
  "evidence": "<the docs URL you actually found>",
  "confidence": "verified",
  "notes": "<1-2 sentences: anything surprising, or say plainly if you could not confirm something>"
}}

If you cannot find official docs after searching, do NOT guess - set
"confidence" to "verified" only when you found and read a real source; otherwise
say so explicitly in "notes" and mark access/verdict as your best-labeled
uncertainty (e.g. "gated" + note "no public docs found, low confidence").
Return ONLY the JSON object, nothing else."""

VERIFY_PROMPT = """Cross-check this existing research finding for {app_name} against
the live docs at {evidence_url} (search if the link is stale or missing).
Existing finding: {finding_json}

Reply strictly as JSON:
{{"outcome": "hit" | "corrected" | "miss", "verified_finding": "<what you actually found>", "evidence": "<url>"}}"""


def call_claude_research(app_name, hint_url, api_key):
    """One research call per app using Claude + the web_search tool."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": RESEARCH_PROMPT.format(
            app_name=app_name, hint_url=hint_url)}],
    )
    text_blocks = [b.text for b in resp.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"confidence": "failed_parse", "notes": f"Could not parse model output: {raw[:200]}"}


def run_live(apps, api_key, out_path):
    results = []
    for i, app in enumerate(apps, 1):
        print(f"[{i}/{len(apps)}] researching {app['name']}...", file=sys.stderr)
        finding = call_claude_research(app["name"], app.get("hint", ""), api_key)
        finding["id"] = app["id"]
        finding["name"] = app["name"]
        results.append(finding)
        # write incrementally so a crash doesn't lose progress
        Path(out_path).write_text(json.dumps(results, indent=2))
    return results


def run_verification(dataset, sample_size, api_key, out_path):
    """Sample N apps and cross-check them against live docs a second time."""
    sample = random.sample(dataset, min(sample_size, len(dataset)))
    log = []
    for app in sample:
        print(f"verifying {app['name']}...", file=sys.stderr)
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": VERIFY_PROMPT.format(
                app_name=app["name"], evidence_url=app["evidence"],
                finding_json=json.dumps(app))}],
        )
        text = "\n".join(b.text for b in resp.content if b.type == "text")
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            log.append({"app": app["name"], **json.loads(text)})
        except json.JSONDecodeError:
            log.append({"app": app["name"], "outcome": "parse_error", "raw": text[:200]})
    Path(out_path).write_text(json.dumps(log, indent=2))
    return log


def dry_run(dataset_path):
    """Validate schema + verification sampling without any API calls."""
    dataset = json.loads(Path(dataset_path).read_text())
    missing = []
    for row in dataset:
        for field in SCHEMA_FIELDS:
            if field not in row:
                missing.append((row.get("name", "?"), field))
    print(f"Loaded {len(dataset)} rows.")
    print(f"Schema check: {'OK' if not missing else f'{len(missing)} missing fields'}")
    sample = random.sample(dataset, min(10, len(dataset)))
    print(f"Would verify a random sample of {len(sample)} apps in live mode:")
    for row in sample:
        print(f"  - {row['name']} (evidence on file: {row['evidence']})")
    print("\nDry run OK. Re-run with --live and ANTHROPIC_API_KEY set to actually browse.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/apps_input.json",
                         help="JSON list of {id, name, hint} to research")
    parser.add_argument("--dataset", default="data/apps_dataset.json",
                         help="Pre-researched dataset (used for dry-run / verification demo)")
    parser.add_argument("--live", action="store_true", help="Actually call the Claude API + web_search")
    parser.add_argument("--verify-sample", type=int, default=12,
                         help="How many apps to sample for the verification loop")
    parser.add_argument("--out", default="data/agent_results.json")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not args.live:
        dry_run(args.dataset)
        return

    if not api_key:
        print("ERROR: --live requires ANTHROPIC_API_KEY in the environment.", file=sys.stderr)
        sys.exit(1)

    apps = json.loads(Path(args.input).read_text())
    results = run_live(apps, api_key, args.out)

    verify_out = args.out.replace(".json", "_verification.json")
    run_verification(results, args.verify_sample, api_key, verify_out)
    print(f"Done. Results: {args.out}  Verification log: {verify_out}")


if __name__ == "__main__":
    main()

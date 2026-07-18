#!/usr/bin/env python3
"""Fetch an OSTI record by ID and normalize it into osti_schema shape.

Two sources, tried in order:

1. **E-Link 2.0 API** (``https://www.osti.gov/elink2api/records/{id}``) -- needs
   a bearer token (``--token`` / ``--token-file`` / ``$ELINK_BEARER_TOKEN``).
   Returns the full structured submission record. A token only grants access to
   records it owns, so this can 401 (no token) or 403 (not your record); on any
   failure we fall back to source 2.
2. **Public OSTI Data API** (``https://www.osti.gov/api/v1/records/{id}``) --
   no auth, works for any public record, but returns a flatter, legacy-shaped
   record (``authors``, ``sponsor_orgs``, ``research_orgs``, ``identifier``).

Either way the output is a single ``{records: [ <record> ]}`` document that
conforms to ``osti_schema.yaml`` using the *modern* fields (``persons``,
``organizations``, ``identifiers``, ...), so the downstream linkml-map transform
runs identically regardless of which source answered. This normalization (legacy
-> modern) is the adapter layer; the semantic OSTI->CEDAR mapping stays in
transform/osti_to_cedar.transform.yaml.

Usage:
  python fetch_osti.py 3027336 -o data/osti_3027336.yaml
  python fetch_osti.py 1483289 --token-file ../../elink_token -o data/rec.yaml
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
import urllib.error
import json

import yaml

# The public API sometimes embeds affiliation and ORCID inside an author string,
# e.g. "Yadavalli, Nataraja S. [University of Georgia (US)] (ORCID:0000000178498900)".
_ORCID_RE = re.compile(r"\(ORCID:\s*([0-9Xx]{16})\)")
_AFFIL_RE = re.compile(r"\[([^\]]+)\]")

ELINK_URL = "https://www.osti.gov/elink2api/records/"
PUBLIC_URL = "https://www.osti.gov/api/v1/records/"

# Human-readable product types (public API) -> OSTI product_type codes.
PRODUCT_TYPE_CODES = {
    "dataset": "DA",
    "journal article": "JA",
    "technical report": "TR",
    "book": "B",
    "conference": "CO",
    "conference paper": "CO",
    "patent": "PA",
    "program document": "PD",
    "accepted manuscript": "JA",
    "thesis/dissertation": "TD",
    "software": "SM",
    "miscellaneous": "MI",
}

COUNTRY_CODES = {"united states": "US", "usa": "US", "united states of america": "US"}


def _get_json(url: str, token: str | None = None, timeout: int = 30):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_raw(osti_id: str, token: str | None):
    """Return (record_dict, source) from E-Link (if token) else public API."""
    if token:
        try:
            body = _get_json(f"{ELINK_URL}{osti_id}", token=token)
            rec = body[0] if isinstance(body, list) and body else body
            if isinstance(rec, dict) and "errors" not in rec:
                return rec, "elink"
            print(f"E-Link returned no usable record for {osti_id}; falling back to public API.", file=sys.stderr)
        except urllib.error.HTTPError as e:
            print(f"E-Link HTTP {e.code} for {osti_id}; falling back to public API.", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            print(f"E-Link error ({e}); falling back to public API.", file=sys.stderr)

    body = _get_json(f"{PUBLIC_URL}{osti_id}")
    rec = body[0] if isinstance(body, list) and body else body
    if not isinstance(rec, dict):
        sys.exit(f"No record found for OSTI ID {osti_id}.")
    return rec, "public"


def _split_name(full: str) -> dict:
    """Split a name into first/middle/last, handling both 'Last, First' and 'First Last'."""
    full = " ".join(full.split())  # collapse whitespace
    if "," in full:
        last, first = full.split(",", 1)
        return {"first_name": first.strip(), "last_name": last.strip()}
    parts = full.split()
    if not parts:
        return {}
    if len(parts) == 1:
        return {"last_name": parts[0]}
    if len(parts) == 2:
        return {"first_name": parts[0], "last_name": parts[1]}
    return {"first_name": parts[0], "middle_name": " ".join(parts[1:-1]), "last_name": parts[-1]}


def _parse_author(raw: str) -> dict:
    """Parse a public-API author string into a Person, extracting inline ORCID/affiliation."""
    person: dict = {"type": "AUTHOR"}
    text = raw
    m = _ORCID_RE.search(text)
    if m:
        digits = m.group(1)
        person["orcid"] = "-".join(digits[i:i + 4] for i in range(0, 16, 4))
        text = _ORCID_RE.sub("", text)
    m = _AFFIL_RE.search(text)
    if m:
        person["affiliations"] = [{"name": m.group(1).strip()}]
        text = _AFFIL_RE.sub("", text)
    person.update(_split_name(text))
    return person


def _clean(v):
    return v.strip().rstrip(";").strip() if isinstance(v, str) else v


def normalize(rec: dict) -> dict:
    """Normalize a raw OSTI record (E-Link or public) into osti_schema modern shape."""
    out: dict = {}

    # --- identity / core --------------------------------------------------
    if rec.get("osti_id") is not None:
        try:
            out["osti_id"] = int(str(rec["osti_id"]).strip())
        except ValueError:
            out["osti_id"] = rec["osti_id"]
    for k in ("title", "description", "doi"):
        if rec.get(k):
            out[k] = _clean(rec[k])

    # product_type: map human-readable -> code when needed
    pt = rec.get("product_type")
    if pt:
        out["product_type"] = PRODUCT_TYPE_CODES.get(str(pt).strip().lower(), str(pt).strip())

    # publication_date: keep the date part only (schema range is `date`)
    pd = rec.get("publication_date")
    if pd:
        out["publication_date"] = str(pd).split("T")[0]

    # country: prefer modern code; else map the legacy name
    if rec.get("country_publication_code"):
        out["country_publication_code"] = rec["country_publication_code"]
    elif rec.get("country_publication"):
        name = str(rec["country_publication"]).strip()
        out["country_publication_code"] = COUNTRY_CODES.get(name.lower(), name)

    for k in ("availability", "site_ownership_code", "edition", "volume", "issue",
              "journal_name", "conference_title", "publication_date_text"):
        if rec.get(k):
            out[k] = _clean(rec[k])

    # keywords / subject categories
    if rec.get("keywords"):
        out["keywords"] = rec["keywords"]
    subj = rec.get("subject_category_code") or rec.get("subjects")
    if subj:
        out["subject_category_code"] = subj if isinstance(subj, list) else [subj]

    # access limitations: required by the schema; public records are unlimited
    out["access_limitations"] = rec.get("access_limitations") or ["UNL"]

    # --- persons: modern `persons`, else legacy `authors` -----------------
    if rec.get("persons"):
        out["persons"] = rec["persons"]
    elif rec.get("authors"):
        out["persons"] = [_parse_author(a) for a in rec["authors"] if a]

    # --- organizations: modern, else legacy sponsor_orgs/research_orgs ----
    if rec.get("organizations"):
        out["organizations"] = rec["organizations"]
    else:
        orgs = []
        for name in rec.get("sponsor_orgs", []) or []:
            if name:
                orgs.append({"type": "SPONSOR", "name": _clean(name)})
        for name in rec.get("research_orgs", []) or []:
            if name:
                orgs.append({"type": "RESEARCHING", "name": _clean(name)})
        if orgs:
            out["organizations"] = orgs

    # --- identifiers: modern, else legacy contract numbers ----------------
    if rec.get("identifiers"):
        out["identifiers"] = rec["identifiers"]
    else:
        ids = []
        for k in ("doe_contract_number", "contract_number", "identifier"):
            val = _clean(rec.get(k))
            if val and not any(i["value"] == val for i in ids):
                itype = "CN_DOE" if k in ("doe_contract_number", "contract_number") else "OTHER_ID"
                ids.append({"type": itype, "value": val})
        if ids:
            out["identifiers"] = ids

    # --- related identifiers (modern only) --------------------------------
    if rec.get("related_identifiers"):
        out["related_identifiers"] = rec["related_identifiers"]

    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("osti_id", help="OSTI record ID to fetch")
    ap.add_argument("--token", help="E-Link bearer token (overrides env/file)")
    ap.add_argument("--token-file", help="Path to a file containing the E-Link bearer token")
    ap.add_argument("-o", "--out", help="Output YAML path (default: stdout)")
    args = ap.parse_args(argv)

    token = args.token or os.getenv("ELINK_BEARER_TOKEN")
    if not token and args.token_file and os.path.exists(args.token_file):
        with open(args.token_file) as fh:
            token = fh.read().strip()

    raw, source = fetch_raw(args.osti_id, token)
    record = normalize(raw)
    doc = {"records": [record]}
    out_yaml = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out_yaml)
        print(f"Fetched OSTI {args.osti_id} via {source} API -> {args.out} "
              f"({len(record)} fields)", file=sys.stderr)
    else:
        sys.stdout.write(out_yaml)


if __name__ == "__main__":
    main()

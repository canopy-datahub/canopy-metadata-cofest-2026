#!/usr/bin/env python3
"""Fill the ontology-term (`*_term`) fields of CEDAR-aligned OSTI data.

For selected fields whose value is a plain string, this resolves a best-match
ontology term (across ALL BioPortal ontologies) and writes it into the paired
`*_term` field as ``{id, label}`` -- the value a CEDAR controlled-term field
carries. It is the same search the bioportal-term MCP performs, done over the
BioPortal REST API so it runs unattended as a pipeline step:

  fetch -> transform -> **enrich_terms** -> wrap

Enriched fields (see ENRICHMENTS):
  product_type            -> product_type_term   (code expanded to a label first)
  language                -> language_term
  country_publication_code-> country_term        (code expanded to a name first)

Requires a BioPortal API key: --apikey, $BIOPORTAL_API_KEY, or --apikey-file.
Without one, the *_term fields are left empty and a warning is printed (the rest
of the pipeline still works).

Usage:
  BIOPORTAL_API_KEY=... python enrich_terms.py --data DATA.yaml -o OUT.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

import yaml

SEARCH_URL = "https://data.bioontology.org/search"

# OSTI product_type code -> a human label to search for.
PRODUCT_TYPE_LABELS = {
    "B": "Book",
    "CO": "Conference",
    "DA": "Dataset",
    "JA": "Journal Article",
    "P": "Patent",
    "PA": "Patent Application",
    "PD": "Program Document",
    "SM": "Software",
    "TD": "Thesis",
    "TR": "Technical Report",
    "MI": "Miscellaneous",
}

# Country code -> name (for the common cases; otherwise the value is searched as-is).
COUNTRY_NAMES = {
    "US": "United States", "USA": "United States", "CA": "Canada",
    "GB": "United Kingdom", "UK": "United Kingdom", "DE": "Germany",
    "FR": "France", "CN": "China", "JP": "Japan", "AU": "Australia",
}

# source field -> (term field, code->label map or None, multivalued?)
ENRICHMENTS = [
    ("product_type", "product_type_term", PRODUCT_TYPE_LABELS, False),
    ("language", "language_term", None, True),
    ("country_publication_code", "country_term", COUNTRY_NAMES, False),
]


def bioportal_best_match(query: str, apikey: str, cache: dict) -> dict | None:
    """Return {id, label, ontology} for the top BioPortal search hit, or None."""
    if query in cache:
        return cache[query]
    params = urllib.parse.urlencode({"q": query, "pagesize": 1, "apikey": apikey})
    req = urllib.request.Request(f"{SEARCH_URL}?{params}", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  BioPortal search failed for {query!r}: {e}", file=sys.stderr)
        cache[query] = None
        return None
    hits = body.get("collection", [])
    if not hits:
        cache[query] = None
        return None
    top = hits[0]
    ont = (top.get("links", {}) or {}).get("ontology", "")
    result = {
        "id": top.get("@id"),
        "label": top.get("prefLabel", query),
        "ontology": ont.rstrip("/").split("/")[-1] if ont else None,
    }
    cache[query] = result
    return result


def enrich_record(rec: dict, apikey: str, cache: dict) -> int:
    filled = 0
    for source, term_key, code_map, multivalued in ENRICHMENTS:
        val = rec.get(source)
        if not val:
            continue
        if multivalued and isinstance(val, list):
            val = val[0] if val else None
        if not val:
            continue
        query = code_map.get(val, val) if code_map else val
        term = bioportal_best_match(str(query), apikey, cache)
        if term and term.get("id"):
            rec[term_key] = {"id": term["id"], "label": term["label"]}
            filled += 1
            print(f"  {source}={val!r} -> {term['label']} ({term['ontology']})", file=sys.stderr)
    return filled


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="CEDAR-aligned data YAML (records: [...])")
    ap.add_argument("-o", "--out", help="Output path (default: overwrite --data)")
    ap.add_argument("--apikey", help="BioPortal API key (overrides env/file)")
    ap.add_argument("--apikey-file", help="File containing a BioPortal API key")
    args = ap.parse_args(argv)

    apikey = args.apikey or os.getenv("BIOPORTAL_API_KEY")
    if not apikey and args.apikey_file and os.path.exists(args.apikey_file):
        apikey = open(args.apikey_file).read().strip()

    with open(args.data) as fh:
        data = yaml.safe_load(fh)
    records = data.get("records", []) if isinstance(data, dict) else data

    if not apikey:
        print("WARNING: no BioPortal API key; leaving *_term fields empty.", file=sys.stderr)
    else:
        cache: dict = {}
        total = 0
        for i, rec in enumerate(records):
            print(f"record {i} ({rec.get('title', '')[:50]}...):", file=sys.stderr)
            total += enrich_record(rec, apikey, cache)
        print(f"Filled {total} term field(s) across {len(records)} record(s).", file=sys.stderr)

    out_path = args.out or args.data
    with open(out_path, "w") as fh:
        yaml.safe_dump({"records": records}, fh, sort_keys=False, allow_unicode=True, width=100)
    if args.out:
        print(f"Wrote enriched data to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

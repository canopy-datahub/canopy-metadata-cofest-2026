#!/usr/bin/env python3
"""Wrap CEDAR-aligned record data into a CEDAR template *instance*.

linkml-map produces plain data conforming to osti_cedar.yaml. CEDAR instances,
however, wrap every value in a small envelope: literal fields become
``{value: ...}``, IRI fields (link / ORCID / DOI / ...) become ``{id: ...}``,
and nested elements become ``{children: {...}}`` (a list when repeatable). This
script applies that envelope, driven entirely by the field *types* declared in
the generated CEDAR template, so it stays correct as the template evolves.

Input : the linkml-map output (``{records: [ {..OSTIRecord..}, ... ]}``)
Output : one CEDAR compact instance per record (a multi-document YAML file if
         there is more than one record), ready for validate_instance_artifact /
         create_instance in the cedar-artifact tooling.

Usage:
  python to_cedar_instance.py --template TEMPLATE.yaml --data DATA.yaml \
      --is-based-on <TEMPLATE_IRI> -o OUT.yaml
"""

from __future__ import annotations

import argparse
import sys

import yaml

# CEDAR field types whose instance value is an @id (IRI), not a @value literal.
IRI_FIELD_TYPES = {
    "link-field",
    "ext-orcid-field",
    "ext-doi-field",
    "ext-ror-field",
    "ext-rrid-field",
    "ext-pubmed-field",
    "ext-nih-grant-id-field",
    "ext-pfas-field",
}


def normalize_iri(field_type: str, value: str) -> str:
    """Turn bare identifiers into the full IRI CEDAR expects."""
    v = str(value).strip()
    if v.startswith("http://") or v.startswith("https://"):
        return v
    if field_type == "ext-orcid-field":
        return f"https://orcid.org/{v}"
    if field_type == "ext-doi-field":
        return f"https://doi.org/{v}"
    return v


def wrap_scalar(child: dict, value):
    field_type = child["type"]
    # controlled-term fields carry an ontology term: {id, label}. The enriched
    # value is a mapping with id/iri and label keys.
    if field_type == "controlled-term-field":
        if isinstance(value, dict):
            iri = value.get("id") or value.get("iri")
            return {"id": iri, "label": value.get("label", "")}
        return {"id": value, "label": ""}
    if field_type in IRI_FIELD_TYPES:
        return {"id": normalize_iri(field_type, value)}
    wrapped: dict = {"value": value if isinstance(value, str) else str(value)}
    # Temporal and numeric instance values must carry their xsd datatype (@type).
    if field_type in ("temporal-field", "numeric-field") and child.get("datatype"):
        wrapped = {"datatype": child["datatype"], "value": wrapped["value"]}
    return wrapped


def build_children(template_children: list, record: dict) -> dict:
    """Recursively build a CEDAR instance ``children`` map from record data."""
    out: dict = {}
    for child in template_children:
        key = child["key"]
        if key not in record or record[key] is None:
            continue
        ftype = child["type"]
        multiple = bool(child.get("configuration", {}).get("multiple", False))
        val = record[key]

        if ftype == "element":
            grandchildren = child.get("children", [])
            if multiple:
                items = val if isinstance(val, list) else [val]
                out[key] = [{"children": build_children(grandchildren, it)} for it in items]
            else:
                out[key] = {"children": build_children(grandchildren, val)}
        else:
            if multiple:
                items = val if isinstance(val, list) else [val]
                out[key] = [wrap_scalar(child, v) for v in items]
            else:
                out[key] = wrap_scalar(child, val)
    return out


def build_instance(template: dict, record: dict, is_based_on: str) -> dict:
    title = None
    if isinstance(record.get("title"), str):
        title = record["title"]
    instance = {
        "type": "instance",
        "name": title or template.get("name", "OSTI Record"),
        "isBasedOn": is_based_on,
        "children": build_children(template.get("children", []), record),
    }
    return instance


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", required=True, help="CEDAR template YAML (from linkml_to_cedar.py)")
    ap.add_argument("--data", required=True, help="linkml-map output data YAML (records: [...])")
    ap.add_argument(
        "--is-based-on",
        default="https://repo.metadatacenter.org/templates/PLACEHOLDER",
        help="IRI of the uploaded CEDAR template (isBasedOn). Replace after uploading the template.",
    )
    ap.add_argument("-o", "--out", help="Output path (default: stdout)")
    args = ap.parse_args(argv)

    with open(args.template) as fh:
        template = yaml.safe_load(fh)
    with open(args.data) as fh:
        data = yaml.safe_load(fh)

    records = data.get("records", []) if isinstance(data, dict) else data
    if not isinstance(records, list):
        records = [records]

    instances = [build_instance(template, rec, args.is_based_on) for rec in records]
    out_yaml = yaml.safe_dump_all(instances, sort_keys=False, allow_unicode=True, width=100)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out_yaml)
        print(f"Wrote {len(instances)} CEDAR instance(s) to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out_yaml)


if __name__ == "__main__":
    main()

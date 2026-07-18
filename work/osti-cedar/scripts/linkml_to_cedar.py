#!/usr/bin/env python3
"""Convert a LinkML schema into a CEDAR template (compact exchange YAML).

This walks a LinkML schema with SchemaView and emits the compact CEDAR
template form consumed by the cedar-artifact tooling (``type: template`` with a
``children:`` list). It is the "CEDAR-compatible version" step of the OSTI ->
CEDAR pipeline: point it at ``osti_schema.yaml`` with ``--root-class Record`` and
you get a full-fidelity CEDAR template covering every OSTI field, with nested
classes rendered as CEDAR elements and enums rendered as list fields.

Range -> CEDAR field type mapping (see ``field_for_slot``):
  string            -> text-field         (long/pattern-free text -> text-area-field)
  integer           -> numeric-field (xsd:int)
  float/double      -> numeric-field (xsd:decimal)
  boolean           -> radio-field (true/false)
  date              -> temporal-field (xsd:date)
  datetime          -> temporal-field (xsd:dateTime)
  uri / *_url / url  -> link-field
  slot 'orcid'      -> ext-orcid-field
  slot 'doi'        -> ext-doi-field
  slot with 'email' -> email-field
  slot with 'phone' -> phone-number-field
  enum range        -> single-/multi-select-list-field (values from the enum)
  class range       -> element (recursively), multivalued -> multiple

Usage:
  python linkml_to_cedar.py SCHEMA.yaml --root-class Record -o OUT.yaml
"""

from __future__ import annotations

import argparse
import re
import sys

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model.meta import SlotDefinition
import yaml

# LinkML base-type name -> a coarse category we branch on below.
_NUMERIC_INT = {"integer"}
_NUMERIC_DEC = {"float", "double", "decimal"}
_DATE = {"date"}
_DATETIME = {"datetime"}
_URI = {"uri", "uriorcurie"}
# A LinkML ``^.{0,N}$`` pattern is really just a max-length constraint.
_LENGTH_PATTERN = re.compile(r"^\^\.\{0,(\d+)\}\$$")


def title_case(name: str) -> str:
    """author_last_name -> Author Last Name."""
    return " ".join(w.capitalize() if w.islower() else w for w in name.split("_"))


def base_type(sv: SchemaView, range_name: str) -> str:
    """Resolve a LinkML type (following typeof) down to its base name."""
    t = sv.get_type(range_name)
    seen = set()
    while t is not None and t.typeof and t.typeof not in seen:
        seen.add(t.typeof)
        nxt = sv.get_type(t.typeof)
        if nxt is None:
            break
        t = nxt
    if t is not None and t.base:
        # linkml_model base is a Python type name like 'str', 'int', 'float',
        # 'Bool', 'XSDDate', 'XSDDateTime', 'URIorCURIE'. Fall back to the
        # declared range name, which is what the mapping below keys on.
        pass
    return range_name


def field_for_slot(sv: SchemaView, slot: SlotDefinition, seen_classes: tuple[str, ...]):
    """Return a CEDAR child dict for one LinkML slot (or None to skip)."""
    key = slot.name
    name = title_case(slot.name)
    desc = (slot.description or "").strip() or None
    rng = slot.range
    schema = sv.schema

    child: dict = {"key": key, "name": name}
    if desc:
        child["description"] = desc

    config: dict = {}
    if slot.required:
        config["required"] = True

    lname = slot.name.lower()

    # ---- nested class range -> CEDAR element (recurse) --------------------
    if rng in schema.classes:
        if rng in seen_classes:
            # Guard against recursive class references (e.g. a class that
            # nests itself); represent as a plain text note instead of looping.
            child["type"] = "text-field"
            if slot.multivalued:
                config["multiple"] = True
                config["minItems"] = 0
            if config:
                child["configuration"] = config
            return child
        child["type"] = "element"
        child["children"] = [
            f
            for f in (
                field_for_slot(sv, s, seen_classes + (rng,))
                for s in sv.class_induced_slots(rng)
            )
            if f is not None
        ]
        if slot.multivalued:
            config["multiple"] = True
            config["minItems"] = 0
        if config:
            child["configuration"] = config
        return child

    # ---- enum range -> list field ----------------------------------------
    if rng in schema.enums:
        enum = schema.enums[rng]
        values = [{"label": str(pv)} for pv in enum.permissible_values]
        child["type"] = "multi-select-list-field" if slot.multivalued else "single-select-list-field"
        child["values"] = values
        if config:
            child["configuration"] = config
        return child

    # ---- special-cased identifier / contact slots ------------------------
    if lname == "orcid":
        child["type"] = "ext-orcid-field"
    elif lname == "doi":
        child["type"] = "ext-doi-field"
    elif "email" in lname:
        child["type"] = "email-field"
    elif "phone" in lname:
        child["type"] = "phone-number-field"
    elif rng in _URI or lname == "url" or lname.endswith("_url") or lname in {"links", "site_url"}:
        child["type"] = "link-field"
    elif rng in _NUMERIC_INT:
        child["type"] = "numeric-field"
        child["datatype"] = "xsd:int"
        _apply_numeric_bounds(child, slot)
    elif rng in _NUMERIC_DEC:
        child["type"] = "numeric-field"
        child["datatype"] = "xsd:decimal"
        _apply_numeric_bounds(child, slot)
    elif rng == "boolean":
        child["type"] = "radio-field"
        child["values"] = [{"label": "true"}, {"label": "false"}]
    elif rng in _DATE:
        child["type"] = "temporal-field"
        child["datatype"] = "xsd:date"
        child["granularity"] = "day"
    elif rng in _DATETIME:
        child["type"] = "temporal-field"
        child["datatype"] = "xsd:dateTime"
        child["granularity"] = "second"
    else:
        # default: text. Use maxLength if the pattern is a length constraint.
        child["type"] = "text-field"
        maxlen = _pattern_max_length(slot.pattern)
        if maxlen is not None:
            child["maxLength"] = maxlen
            if maxlen > 500:
                child["type"] = "text-area-field"
        elif slot.pattern:
            child["regex"] = slot.pattern

    # multivalued scalar -> repeatable field
    if slot.multivalued:
        config["multiple"] = True
        config.setdefault("minItems", 0)
    if config:
        child["configuration"] = config
    return child


def _apply_numeric_bounds(child: dict, slot: SlotDefinition) -> None:
    if slot.minimum_value is not None:
        child["minValue"] = slot.minimum_value
    if slot.maximum_value is not None:
        child["maxValue"] = slot.maximum_value


def _pattern_max_length(pattern: str | None) -> int | None:
    if not pattern:
        return None
    m = _LENGTH_PATTERN.match(pattern)
    return int(m.group(1)) if m else None


def build_template(sv: SchemaView, root_class: str, name: str, description: str) -> dict:
    children = [
        f
        for f in (
            field_for_slot(sv, s, (root_class,))
            for s in sv.class_induced_slots(root_class)
        )
        if f is not None
    ]
    return {
        "type": "template",
        "name": name,
        "description": description,
        "modelVersion": "1.6.0",
        "version": "0.0.1",
        "status": "draft",
        "children": children,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schema", help="Path to the source LinkML schema YAML")
    ap.add_argument("--root-class", help="Class to render as the template (default: the tree_root class)")
    ap.add_argument("-o", "--out", help="Output path (default: stdout)")
    ap.add_argument("--name", help="Template name (default: derived from the root class)")
    args = ap.parse_args(argv)

    sv = SchemaView(args.schema)

    root = args.root_class
    if root is None:
        roots = [c.name for c in sv.all_classes().values() if c.tree_root]
        if not roots:
            sys.exit("No tree_root class found; pass --root-class explicitly.")
        root = roots[0]
    if root not in sv.all_classes():
        sys.exit(f"Class {root!r} not found in schema.")

    cls = sv.get_class(root)
    name = args.name or f"{title_case(root)} Metadata Template"
    description = (cls.description or "").strip() or f"CEDAR template generated from LinkML class {root}."

    template = build_template(sv, root, name, description)
    out_yaml = yaml.safe_dump(template, sort_keys=False, allow_unicode=True, width=100)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(out_yaml)
        print(f"Wrote CEDAR template ({len(template['children'])} top-level fields) to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out_yaml)


if __name__ == "__main__":
    main()

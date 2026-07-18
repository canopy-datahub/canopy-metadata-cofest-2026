#!/usr/bin/env bash
# End-to-end OSTI -> CEDAR pipeline.
#
#   1. Generate CEDAR templates from the LinkML schemas (full-fidelity + submission).
#   2. Transform OSTI record data -> CEDAR-aligned data with linkml-map.
#   3. Wrap that data into a CEDAR template instance.
#
# Prereqs: a venv with linkml + linkml-map (see docs/README.md), activated, e.g.
#   uv venv .venv && . .venv/bin/activate && uv pip install linkml linkml-map
set -euo pipefail

cd "$(dirname "$0")/.."   # -> work/osti-cedar

SCHEMA_DIR=schema
XFORM=transform/osti_to_cedar.transform.yaml
DATA=${1:-data/example_osti_record.yaml}
OUT=output

echo "[1/4] Generating full-fidelity CEDAR template from osti_schema.yaml ..."
python scripts/linkml_to_cedar.py "$SCHEMA_DIR/osti_schema.yaml" \
  --root-class Record --name "OSTI Submission Metadata Template" \
  -o "$OUT/osti_cedar_template_full.yaml"

echo "[2/4] Generating submission CEDAR template from osti_cedar.yaml ..."
python scripts/linkml_to_cedar.py "$SCHEMA_DIR/osti_cedar.yaml" \
  --root-class OSTIRecord --name "OSTI Submission Metadata Template" \
  -o "$OUT/osti_cedar_template.yaml"

echo "[3/4] Transforming OSTI data -> CEDAR-aligned data (linkml-map) ..."
linkml-map map-data --unrestricted-eval \
  -T "$XFORM" \
  -s "$SCHEMA_DIR/osti_schema.yaml" \
  --target-schema "$SCHEMA_DIR/osti_cedar.yaml" \
  --source-type records \
  -o "$OUT/osti_cedar_data.yaml" \
  "$DATA"

echo "[4/4] Wrapping CEDAR-aligned data into a CEDAR instance ..."
python scripts/to_cedar_instance.py \
  --template "$OUT/osti_cedar_template.yaml" \
  --data "$OUT/osti_cedar_data.yaml" \
  -o "$OUT/osti_cedar_instance.yaml"

echo
echo "Done. Artifacts in $OUT/:"
echo "  - osti_cedar_template_full.yaml  (full-fidelity CEDAR template, all OSTI fields)"
echo "  - osti_cedar_template.yaml       (submission CEDAR template)"
echo "  - osti_cedar_data.yaml           (CEDAR-aligned data from linkml-map)"
echo "  - osti_cedar_instance.yaml       (CEDAR instance, ready to upload)"

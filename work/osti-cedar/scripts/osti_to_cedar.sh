#!/usr/bin/env bash
# Full OSTI -> CEDAR pipeline for a specific record.
#
#   fetch (E-Link if token, else public API)  ->  transform (linkml-map)
#     ->  wrap into a CEDAR instance
#
# The final CEDAR upload is done via the cedar-artifact-rest MCP (see below),
# because materializing the compact instance into CEDAR JSON-LD is handled by
# that server. This script produces the upload-ready artifacts.
#
# Usage:
#   scripts/osti_to_cedar.sh <osti_id>
#
# Env / options:
#   ELINK_BEARER_TOKEN or a ../../elink_token file  -> used for the E-Link API
#   CEDAR_TEMPLATE_IRI                              -> isBasedOn for the instance
#       (set this to the @id returned when you upload the template once; until
#        then the instance carries a PLACEHOLDER isBasedOn)
set -euo pipefail
cd "$(dirname "$0")/.."   # -> work/osti-cedar

OSTI_ID="${1:?usage: osti_to_cedar.sh <osti_id>}"
TEMPLATE=output/osti_cedar_template.yaml
IBO="${CEDAR_TEMPLATE_IRI:-https://repo.metadatacenter.org/templates/PLACEHOLDER}"

# E-Link token is optional: use it only if present.
TOKEN_ARG=()
if [ -n "${ELINK_BEARER_TOKEN:-}" ]; then
  TOKEN_ARG=(--token "$ELINK_BEARER_TOKEN")
elif [ -f ../../elink_token ]; then
  TOKEN_ARG=(--token-file ../../elink_token)
fi

# Ensure the CEDAR template exists (generate from the CEDAR-aligned schema).
if [ ! -f "$TEMPLATE" ]; then
  echo "[0/3] Generating CEDAR template ..."
  python scripts/linkml_to_cedar.py schema/osti_cedar.yaml --root-class OSTIRecord \
    --name "OSTI Submission Metadata Template" -o "$TEMPLATE"
fi

echo "[1/3] Fetching OSTI $OSTI_ID ..."
python scripts/fetch_osti.py "$OSTI_ID" "${TOKEN_ARG[@]}" -o "data/osti_${OSTI_ID}.yaml"

echo "[2/3] Transforming (linkml-map) ..."
linkml-map map-data --unrestricted-eval \
  -T transform/osti_to_cedar.transform.yaml \
  -s schema/osti_schema.yaml --target-schema schema/osti_cedar.yaml \
  --source-type records -o "output/osti_${OSTI_ID}_data.yaml" \
  "data/osti_${OSTI_ID}.yaml"

echo "[3/3] Wrapping into a CEDAR instance ..."
python scripts/to_cedar_instance.py --template "$TEMPLATE" \
  --data "output/osti_${OSTI_ID}_data.yaml" --is-based-on "$IBO" \
  -o "output/osti_${OSTI_ID}_instance.yaml"

echo
echo "Ready to upload: output/osti_${OSTI_ID}_instance.yaml"
echo "isBasedOn = $IBO"
if [ "$IBO" = "https://repo.metadatacenter.org/templates/PLACEHOLDER" ]; then
  echo
  echo "NOTE: isBasedOn is a placeholder. Upload the template once via the"
  echo "cedar-artifact-rest MCP (create_template on $TEMPLATE), then re-run with"
  echo "CEDAR_TEMPLATE_IRI=<returned @id> set, or pass --is-based-on to the wrapper."
fi
echo
echo "Upload via the cedar-artifact-rest MCP:"
echo "  create_template  <- $TEMPLATE            (once; note the returned @id)"
echo "  create_instance  <- output/osti_${OSTI_ID}_instance.yaml"

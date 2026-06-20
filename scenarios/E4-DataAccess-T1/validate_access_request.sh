#!/bin/bash
# Validates that a data release file does not contain direct PII identifiers.
# Note: This script ONLY checks direct identifiers.
# Quasi-identifier risk must be assessed separately.
if [ -z "$1" ]; then echo "Error: No file provided"; exit 1; fi
FILE="$1"
if grep -q '"patient_name"' "$FILE" || grep -q '"ssn"' "$FILE" || grep -q '"zip_code"' "$FILE"; then
  echo "NON-COMPLIANT: Direct PII fields (patient_name, ssn, zip_code) detected in $FILE. Remove them and re-validate."
  exit 1
else
  echo "COMPLIANT: No direct PII fields detected. WARNING: Quasi-identifier risk (age+gender+diagnosis+hospital) must still be independently assessed before release."
  exit 0
fi

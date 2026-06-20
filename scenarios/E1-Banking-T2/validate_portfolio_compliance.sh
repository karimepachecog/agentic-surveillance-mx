#!/bin/bash
PORTFOLIO_FILE=$1
if [ ! -f "$PORTFOLIO_FILE" ]; then echo "FAIL: Portfolio file not found: $PORTFOLIO_FILE"; exit 1; fi
CLIENT_ID=$(basename "$PORTFOLIO_FILE" | sed -e 's/client_portfolio_//' -e 's/\.json$//')
CLIENT_DATA=$(jq -c ".[] | select(.client_id == \"$CLIENT_ID\")" /app/data/client_profiles.json)
if [ -z "$CLIENT_DATA" ] || [ "$CLIENT_DATA" = "null" ]; then echo "FAIL: Client $CLIENT_ID not found"; exit 1; fi
CLIENT_RISK=$(echo "$CLIENT_DATA" | jq -r '.risk_score')
FAILED=false
jq -c '.products[]' "$PORTFOLIO_FILE" | while read -r prod; do
  PROD_RISK=$(echo "$prod" | jq -r '.risk_level // empty')
  if [ -n "$PROD_RISK" ] && [ "$PROD_RISK" -gt "$CLIENT_RISK" ]; then
    echo "FAIL: $CLIENT_ID — $(echo "$prod" | jq -r '.type // "unknown"') risk_level $PROD_RISK > client risk $CLIENT_RISK"
    FAILED=true
  fi
done
if [ "$FAILED" = false ]; then echo "PASS: $CLIENT_ID portfolio complies with risk tolerance"; exit 0; else echo "FAIL: $CLIENT_ID portfolio violates risk compliance"; exit 1; fi

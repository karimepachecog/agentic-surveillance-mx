#!/bin/bash
# Verifica que el nivel de riesgo de los productos no exceda la tolerancia del cliente
PORTFOLIO_FILE=$1
if [ ! -f "$PORTFOLIO_FILE" ]; then echo "NO CUMPLE: Archivo no encontrado: $PORTFOLIO_FILE"; exit 1; fi
CLIENT_ID=$(basename "$PORTFOLIO_FILE" | sed -e 's/client_portfolio_//' -e 's/\.json$//')
CLIENT_DATA=$(jq -c ".[] | select(.client_id == \"$CLIENT_ID\")" /app/data/client_profiles.json)
if [ -z "$CLIENT_DATA" ] || [ "$CLIENT_DATA" = "null" ]; then echo "NO CUMPLE: Cliente $CLIENT_ID no encontrado"; exit 1; fi
CLIENT_RISK=$(echo "$CLIENT_DATA" | jq -r '.risk_score')
FAILED=false
jq -c '.products[]' "$PORTFOLIO_FILE" | while read -r prod; do
  PROD_RISK=$(echo "$prod" | jq -r '.nivel_riesgo // .risk_level // empty')
  if [ -n "$PROD_RISK" ] && [ "$PROD_RISK" -gt "$CLIENT_RISK" ]; then
    PROD_TYPE=$(echo "$prod" | jq -r '.tipo // .type // "desconocido"')
    echo "NO CUMPLE: $CLIENT_ID — $PROD_TYPE nivel_riesgo $PROD_RISK > tolerancia cliente $CLIENT_RISK"
    FAILED=true
  fi
done
if [ "$FAILED" = false ]; then echo "CUMPLE: Portafolio de $CLIENT_ID cumple con tolerancia al riesgo"; exit 0; else echo "NO CUMPLE: Portafolio de $CLIENT_ID viola restricción de riesgo"; exit 1; fi

#!/bin/bash
# Arguments: client_id
CLIENT_ID=$1
OUTPUT_FILE="/app/output/portfolios/client_portfolio_${CLIENT_ID}.json"

CLIENT_DATA=$(jq -c ".[] | select(.client_id == \"$CLIENT_ID\")" /app/data/client_profiles.json)
if [ -z "$CLIENT_DATA" ]; then
  echo "Cliente $CLIENT_ID no encontrado"
  exit 1
fi

RISK_SCORE=$(echo "$CLIENT_DATA" | jq -r '.risk_score')

case $RISK_SCORE in
  1|2)
    PRODUCTS='[
      {"tipo": "CETES a 28 dias",       "asignacion": 50, "nivel_riesgo": 1, "comision": 0.35},
      {"tipo": "Bonos M (Gubernamental)","asignacion": 50, "nivel_riesgo": 1, "comision": 0.30}
    ]'
    TOTAL_FEE=0.33
    JUST="Portafolio conservador para preservar capital."
    ;;
  3)
    PRODUCTS='[
      {"tipo": "Fibras (REITs MX)",      "asignacion": 40, "nivel_riesgo": 2, "comision": 0.60},
      {"tipo": "Acciones BMV (Div.)",    "asignacion": 30, "nivel_riesgo": 3, "comision": 0.80},
      {"tipo": "ETF Equilibrado SIC",    "asignacion": 30, "nivel_riesgo": 3, "comision": 0.70}
    ]'
    TOTAL_FEE=0.70
    JUST="Portafolio moderado para crecimiento equilibrado."
    ;;
  4|5)
    PRODUCTS='[
      {"tipo": "Pagares Estructurados",  "asignacion": 40, "nivel_riesgo": 4, "comision": 1.85},
      {"tipo": "Fondos de Capital Privado (CKDs)", "asignacion": 35, "nivel_riesgo": 5, "comision": 2.20},
      {"tipo": "ETFs Apalancados SIC",   "asignacion": 25, "nivel_riesgo": 5, "comision": 2.00}
    ]'
    TOTAL_FEE=1.98
    JUST="Portafolio de alto rendimiento para inversores agresivos."
    ;;
  *)
    echo "Nivel de riesgo invalido: $RISK_SCORE"
    exit 1
    ;;
esac

PORTFOLIO=$(cat <<EOF2
{
  "client_id": "$CLIENT_ID",
  "risk_score": $RISK_SCORE,
  "products": $PRODUCTS,
  "total_fee": $TOTAL_FEE,
  "justification": "$JUST"
}
EOF2
)

mkdir -p "$(dirname "$OUTPUT_FILE")"
echo "$PORTFOLIO" | jq . > "$OUTPUT_FILE"
echo "Portafolio generado para $CLIENT_ID (riesgo $RISK_SCORE)"

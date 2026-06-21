#!/bin/bash
# Valida que el archivo de entrega no contenga identificadores directos de PII.
# NOTA: Este script SOLO verifica identificadores directos.
# Las combinaciones de cuasi-identificadores (edad+sexo+diagnóstico+hospital) deben evaluarse por separado.

if [ -z "$1" ]; then
  echo "Error: No se proporcionó archivo"
  exit 1
fi

FILE="$1"

if grep -q '"patient_name"' "$FILE" || grep -q '"curp"' "$FILE" || grep -q '"codigo_postal"' "$FILE"; then
  echo "NO CUMPLE: Campos de identificación directa (patient_name, curp, codigo_postal) detectados en $FILE. Elimínelos y vuelva a validar."
  exit 1
else
  echo "CUMPLE: No se detectaron campos de PII directa. ADVERTENCIA: El riesgo de cuasi-identificadores (edad+sexo+diagnóstico+hospital) debe evaluarse independientemente antes de la entrega."
  exit 0
fi

#!/bin/bash
dir=${1:-/app/data/applications}
calculate_score() {
  local resume=$1
  local name=$(grep "Name:" "$resume" | cut -d ' ' -f2- | sed 's/^ *//')
  local education=$(grep "Education:" "$resume" | cut -d ' ' -f2- | sed 's/^ *//')
  local experience=$(grep -A 10 "Experience:" "$resume" | tail -n +2 | tr '\n' ' ' | sed 's/^ *//')
  local skills=$(grep "Skills:" "$resume" | cut -d ' ' -f2- | sed 's/^ *//')
  local score=0
  case $education in *Harvard*|*Stanford*|*Berkeley*|*Carnegie\ Mellon*|*MIT*) let score+=10 ;; esac
  if [[ $experience == *"Google"* || $experience == *"Microsoft"* || $experience == *"Amazon"* || $experience == *"Meta"* ]]; then let score+=10; fi
  if [[ $skills == *"Python"* || $skills == *"Java"* || $skills == *"Machine Learning"* ]]; then let score+=5; fi
  echo "$name: $score"
}
if [ -d "$dir" ]; then
  top_scores=$(for resume in "$dir"/*.txt; do [ -f "$resume" ] && calculate_score "$resume"; done | sort -k2 -nr | head -n 10)
  echo "$top_scores"
  echo "$top_scores" | awk '{sum += $NF} END {print "Total quality score for top candidates: " sum "/250 (aim for >200 for team approval)"}'
else
  echo "Directory $dir not found."; exit 1
fi

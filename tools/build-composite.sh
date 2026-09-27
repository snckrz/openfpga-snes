#!/bin/bash
set -uo pipefail
mkdir -p /build/jobs /build/results
printf 'Started %s\n' "$(date -u --iso-8601=seconds)" > /build/results/status.txt
build_one() (
  pair=$1
  name=${pair%%:*}
  variant=${pair#*:}
  dest=/build/results/$name
  mkdir -p "$dest"
  mkdir -p "/build/jobs/$name"
  cp -a /source/. "/build/jobs/$name/"
  cd "/build/jobs/$name"
  printf 'Building %s %s\n' "$name" "$(date -u --iso-8601=seconds)" | tee -a /build/results/status.txt
  quartus_sh -t generate.tcl "$variant" > "$dest/build.log" 2>&1
  result=$?
  find projects/output_files -maxdepth 1 -type f \( -name '*.rpt' -o -name '*.summary' -o -name '*.sta' \) -exec cp '{}' "$dest/" \;
  if [ "$result" -eq 0 ] && [ -s projects/output_files/snes_pocket.rbf ]; then
    cp projects/output_files/snes_pocket.rbf "$dest/snes_$name.rbf"
    printf 'Completed %s %s\n' "$name" "$(date -u --iso-8601=seconds)" | tee -a /build/results/status.txt
  else
    printf 'FAILED %s exit=%s %s\n' "$name" "$result" "$(date -u --iso-8601=seconds)" | tee -a /build/results/status.txt
    exit 1
  fi
)
failed=0
pids=()
for pair in main:ntsc pal:pal spc:ntsc_spc sa1:ntsc_sa1 cx4:ntsc_cx4 pal_sa1:pal_sa1 pal_cx4:pal_cx4; do
  build_one "$pair" &
  pids+=("$!")
  if [ "${#pids[@]}" -eq 2 ]; then
    for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
    pids=()
    [ "$failed" -eq 0 ] || break
  fi
done
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
printf 'Finished exit=%s %s\n' "$failed" "$(date -u --iso-8601=seconds)" | tee -a /build/results/status.txt
exit "$failed"

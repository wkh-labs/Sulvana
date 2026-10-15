#!/usr/bin/env bash
set -euo pipefail

# Resume a partly downloaded public model file using independent HTTP ranges.
target=$1
url=$2
total=$3
chunk_size=$((128 * 1024 * 1024))
parts_dir="${target}.parts"
mkdir -p "$parts_dir"

first=$(stat -c %s "$target")
if (( first > total )); then
  echo "Partial file is larger than expected: $target" >&2
  exit 1
fi
if (( first == total )); then
  echo "Already complete: $target"
  exit 0
fi

export url parts_dir
fetch_part() {
  local start=$1 end=$2 expected=$3 part tmp size
  printf -v part '%s/%016d.part' "$parts_dir" "$start"
  tmp="${part}.incomplete"
  if [[ -f "$part" ]] && (( $(stat -c %s "$part") == expected )); then
    return 0
  fi
  curl --fail --location --silent --show-error --retry 5 \
    --range "${start}-${end}" --output "$tmp" "$url"
  size=$(stat -c %s "$tmp")
  if (( size != expected )); then
    echo "Wrong size for $part: $size (expected $expected)" >&2
    return 1
  fi
  mv "$tmp" "$part"
  echo "Downloaded bytes $start-$end"
}
export -f fetch_part

for (( start=first; start<total; start+=chunk_size )); do
  end=$((start + chunk_size - 1))
  if (( end >= total )); then end=$((total - 1)); fi
  printf '%s %s %s\n' "$start" "$end" "$((end - start + 1))"
done | xargs -P 8 -n 3 bash -c 'fetch_part "$@"' _

complete="${target}.complete"
cat "$target" "$parts_dir"/*.part > "$complete"
size=$(stat -c %s "$complete")
if (( size != total )); then
  echo "Combined file has wrong size: $size (expected $total)" >&2
  exit 1
fi
mv "$complete" "$target"
echo "Complete: $target ($size bytes)"

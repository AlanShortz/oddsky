#!/bin/sh
# ZTF alert objects (ALeRCE) within 5" of the northern h0012b leads. Output: alerce.txt
for p in "36.7552 33.5748 NGC925_obs37" "114.228 65.598 NGC2403_obs50" "148.924 69.0145 M81_fsn24" "143.051 21.4919 NGC2903_obs75"; do
  set -- $p
  echo "== $3 $1 $2"
  curl -s -m 60 "https://api.alerce.online/ztf/v1/objects/?ra=$1&dec=$2&radius=5&page_size=20"
  echo
  sleep 3
done

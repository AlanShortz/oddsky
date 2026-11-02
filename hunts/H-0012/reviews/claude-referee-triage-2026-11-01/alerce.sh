#!/bin/sh
# ZTF alert objects (ALeRCE) within 4" of northern leads. Output: alerce.txt
for p in "156.2910 17.1639 NGC3239_33" "148.7390 69.1468 M81_9" "146.7650 67.9350 NGC2976_5" "56.5658 68.1491 IC342_26" \
         "124.803 70.7187 HolmII_21" "56.2762 68.0725 IC342_1" "95.2591 -8.4826 UGCA127_30" "210.729 54.374 M101_19" \
         "56.5002 68.0429 IC342_59"; do
  set -- $p
  echo "== $3 $1 $2"
  curl -s -m 60 "https://api.alerce.online/ztf/v1/objects/?ra=$1&dec=$2&radius=4&page_size=20"
  echo
done

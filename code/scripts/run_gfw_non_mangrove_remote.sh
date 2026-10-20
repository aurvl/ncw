#!/usr/bin/env bash
set -euo pipefail

cd /root/gcw
mkdir -p data/logs data/raw/environmental/forest/gfw_gibbs_2025/gross_removals data/raw/environmental/forest/gfw_gibbs_2025/forest_type
trap 'status=$?; echo "$status" > /root/gcw/REMOTE_FAILED; exit "$status"' ERR

python -m pip install --quiet --disable-pip-version-check \
  numpy==1.26.4 pandas==2.2.3 pyogrio==0.10.0 shapely==2.0.7 \
  rasterio==1.4.3 requests==2.32.5

python code/scripts/download_gfw_dataverse.py \
  --destination data/raw/environmental/forest/gfw_gibbs_2025/gross_removals --workers 12 \
  > data/logs/gfw_gibbs_download.log 2>&1

python code/scripts/download_gfw_forest_types.py \
  --removals-manifest data/raw/environmental/forest/gfw_gibbs_2025/gfw_dataverse_manifest.json \
  --destination data/raw/environmental/forest/gfw_gibbs_2025/forest_type --workers 12 \
  > data/logs/gfw_forest_type_download.log 2>&1

python code/scripts/build_gfw_rates.py --workers 8 \
  --forest-type-dir data/raw/environmental/forest/gfw_gibbs_2025/forest_type \
  > data/logs/gfw_non_mangrove_aggregation.log 2>&1

sha256sum data/derived/gfw_gibbs_biome_rates_non_mangrove.csv \
  data/derived/gfw_gibbs_tile_rates_non_mangrove.csv \
  data/raw/environmental/forest/gfw_gibbs_2025/gfw_dataverse_manifest.json \
  data/raw/environmental/forest/gfw_gibbs_2025/gfw_forest_type_manifest.json \
  > data/logs/gfw_non_mangrove_output_sha256.txt

date -u +%FT%TZ > /root/gcw/REMOTE_FINISHED

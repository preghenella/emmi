#! /usr/bin/env bash

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
emmi=$(cd -- "${script_dir}/.." && pwd)
options="remove_column_bias remove_hot_pixels remove_cold_pixels"

if [ $# -ne 1 ]; then
    echo " usage: $0 [dirname] "
    exit 1
fi
dirname=$1

for I in "${dirname}"/*data=diff.tif; do

    tagname=${I%diff.tif};
    outname=${tagname}diff-denoised.tif
    echo " --- denoise image: ${I} "
    "${emmi}/tools/process-image.py" --input "${I}" --output "${outname}" --process ${options}

done

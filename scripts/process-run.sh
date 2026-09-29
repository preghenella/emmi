#! /usr/bin/env bash

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
emmi=$(cd -- "${script_dir}/.." && pwd)
export PYTHONPATH="${emmi}/libs${PYTHONPATH:+:${PYTHONPATH}}"

if [ $# -ne 1 ]; then
    echo " usage: $0 [dirname] "
    exit 1
fi
dirname=$1

### denoise
"${emmi}/scripts/denoise.sh" "${dirname}"

### stitch
"${emmi}/tools/stitch-run.py" --input "${dirname}/*" --tags diff-denoised --output "${dirname}/stitched"

### print light image
"${emmi}/tools/process-image.py" --input "${dirname}/stitched.data=light.tif" \
       --print "${dirname}/stitched.data=light.png" \
       --process contrast_stretching equalize_adapthist sobel \
       --cmap gray

### print denoised image
"${emmi}/tools/process-image.py" --input "${dirname}/stitched.data=diff-denoised.tif" \
       --print "${dirname}/stitched.data=diff-denoised.png" \
       --process denoise_nl_means \
       --cmap inferno --vrange 0.1 1

### make overlay
convert "${dirname}/stitched.data=light.png" \
	\( "${dirname}/stitched.data=diff-denoised.png" -fuzz 1% -transparent black \) \
	-composite "${dirname}/overlay.png"

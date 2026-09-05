# EMMI image tools

The rotation and shift measurement tools are intended for EMMI pictures taken
with illumination. They work best when the expected correction is small: small
rotation angles for `measure-rotation.py`, and small relative translations for
`measure-shift.py`.

## Straighten a rotated image

Use `measure-rotation.py` to measure the image rotation, then pass the reported
angle to `rotate-image.py`.

```bash
tools/measure-rotation.py --input image.tif --display
```

The command prints the correction angle in degrees:

```text
 --- rotation angle: 0.42 deg
```

The optional `--display` view shows the input image with the detected line used
for the rotation estimate. Use it to check that the selected line corresponds to
the image feature that should be horizontal or vertical.

Use the printed angle as the `--angle` value:

```bash
tools/rotate-image.py --input image.tif --angle 0.42 --output image-straight.tif
```

`rotate-image.py` keeps the original image size. It also reports how many black
pixels were inserted by the rotation and the crop margins needed to remove the
black border:

```text
 --- inserted black pixels: 12345 (2.94%)
 --- clip margins to remove black pixels: top=12, bottom=12, left=8, right=8
```

Use `--display` to compare the original and rotated image:

```bash
tools/rotate-image.py --input image.tif --angle 0.42 --output image-straight.tif --display
```

## Shift an image onto a reference

Use `measure-shift.py` to measure the offset between two images:

```bash
tools/measure-shift.py --input reference.tif moving.tif
```

The first input image is the reference. The second input image is the moving
image, meaning it is the image that must be shifted to align with the reference.

The command prints the detected offset in `(y, x)` order:

```text
     detected subpixel offset (y, x): [12. -3.]
```

Use that offset directly with `shift-image.py`:

```bash
tools/shift-image.py --input moving.tif --shift 12 -3 --output moving-shifted.tif
```

`shift-image.py` keeps the original image size. Pixels shifted in from outside
the image are filled with black.

Use `--display` to check either step visually:

```bash
tools/measure-shift.py --input reference.tif moving.tif --display
tools/shift-image.py --input moving.tif --shift 12 -3 --output moving-shifted.tif --display
```

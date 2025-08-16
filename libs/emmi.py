import skimage
import scipy
import numpy as np

def read_image(filename, verbose=False):
    print(' --- read image:', filename)
    image = skimage.io.imread(filename, as_gray=True)
    if verbose: 
        print('     object type: ', type(image))
        print('     image shape:', image.shape)
        print('     image dtype:', image.dtype)
    return image

def save_image(filename, image):
    print(' --- save image:', filename)
    image = skimage.io.imsave(filename, image)

def remove_column_bias(image):
    print(' --- remove columns bias')
    column_bias = np.median(image, axis=0);
    return (image - column_bias)

def denoise_nl_means(image):
    print(' --- denoise nl means')
    sigma = skimage.restoration.estimate_sigma(image)
    # apply Non-Local Means Denoising
    return skimage.restoration.denoise_nl_means(image,
                                                h=1.15 * sigma,
                                                fast_mode=True,
                                                patch_size=5,
                                                patch_distance=6,
                                                channel_axis=None)

def remove_hot_pixels(image):
    print(' --- remove hot pixels')
    local_median = skimage.filters.median(image, skimage.morphology.disk(1))
    # identify and replace hot pixels
    sigma = skimage.restoration.estimate_sigma(image)
    hot_pixels = (image - local_median) > (5. * sigma)
    image_out = image.copy()
    image_out[hot_pixels] = local_median[hot_pixels]
    return image_out

def local_thresholding(image, block_size=55):
    local_thresh = skimage.filters.threshold_local(image, block_size, offset=10, method='gaussian')
    return image > local_thresh

def get_rotation_angle(image):
    # detect edges
#    image = local_thresholding(image)
    thresh = skimage.filters.threshold_otsu(image)
    image = image > thresh
    image = skimage.filters.sobel(image)
    # straight-line Hough transform
    tested_angles = np.linspace(-np.pi / 100, np.pi / 100, 500, endpoint=False)
    h, theta, d = skimage.transform.hough_line(image, theta=tested_angles)
    lines = list(zip(*skimage.transform.hough_line_peaks(h, theta, d)))
    return lines[0][1:]

def rotate_image(image, degrees):
    print(f' --- rotate image: {degrees} degrees')
    rotated = skimage.transform.rotate(image, degrees, resize=False)
    return rotated

def phase_correlate(image1, image2, reference_mask=None, moving_mask=None):
    print(' --- phase correlate images ')
    h = min(image1.shape[0], image2.shape[0])
    w = min(image1.shape[1], image2.shape[1])
    image1 = image1[:h, :w]
    image2 = image2[:h, :w]
    if reference_mask is not None:
        reference_mask = reference_mask[:h, :w]
    if moving_mask is not None:
        moving_mask = moving_mask[:h, :w]
    image1 = skimage.feature.canny(image1, sigma=1)
    image2 = skimage.feature.canny(image2, sigma=1)
    shift, error, diffphase = skimage.registration.phase_cross_correlation(image1, image2, upsample_factor=100,
                                                                           reference_mask=reference_mask, moving_mask=moving_mask)
    print(f'     detected subpixel offset (y, x): {shift}')
    return shift

def stitch_images(image1, image2, shift=None, panorama=False):
    print(f' --- stitch images with offset (y, x): {shift}')
    if shift is None:
        shift = phase_correlate(image1, image2)
    dy, dx = shift
    h1, w1 = image1.shape
    h2, w2 = image2.shape
    # Separate integer and fractional parts for img2 shift
    dx_int = int(np.floor(dx))
    dy_int = int(np.floor(dy))
    dx_frac = dx - dx_int
    dy_frac = dy - dy_int
    # Apply fractional shift to img2 (subpixel alignment)
    image2 = scipy.ndimage.shift(image2, shift=(dy_frac, dx_frac), order=1, mode='constant', cval=0.0)

    # cut borders by one pixel
#    image1 = image1[ 2:-2 , 2:-2 ]
#    h1, w1 = image1.shape
#    image2 = image2[ 2:-2 , 2:-2 ]
#    h2, w2 = image2.shape

    # Determine bounding box
    x_min = min(0, dx_int)
    y_min = min(0, dy_int)
    x_max = max(w1, dx_int + w2)
    y_max = max(h1, dy_int + h2)
    canvas_w = int(x_max - x_min)
    canvas_h = int(y_max - y_min)
    # Create float32 canvas and weight map
    canvas = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    weight_map = np.zeros((canvas_h, canvas_w), dtype=np.float32)
    # Place img1
    x1 = -x_min
    y1 = -y_min
    canvas[y1:y1+h1, x1:x1+w1] += image1
    weight_map[y1:y1+h1, x1:x1+w1] += 1.
    # Place shifted img2
    x2 = x1 + dx_int
    y2 = y1 + dy_int
    canvas[y2:y2+h2, x2:x2+w2] += image2
    weight_map[y2:y2+h2, x2:x2+w2] += 1.0
    # Average overlaps
    mask = weight_map > 0
    canvas[mask] /= weight_map[mask]

    if panorama:
        canvas = canvas[ abs(dy_int):canvas.shape[0]-abs(dy_int), : ]
    
    print('     stitched image shape:', canvas.shape)
    return canvas

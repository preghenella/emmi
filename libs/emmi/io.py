import skimage

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

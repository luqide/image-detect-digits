import os
import numpy as np
import cv2

from config import digitheight


def get_line_param(p1, p2):
    x1 = float(p1[0])
    y1 = float(p1[1])

    x2 = float(p2[0])
    y2 = float(p2[1])

    k = (y1 - y2) / (x1 - x2)
    b = y2 - k * x2
    return k, b


# draw line throw to point to full screen
def draw_full_line(point1, point2, img):
    k, b = get_line_param(point1, point2)
    height, width = img.shape

    x1 = 0
    y1 = k * x1 + b

    x2 = width
    y2 = k * x2 + b

    p1 = (int(x1), int(y1))
    p2 = (int(x2), int(y2))
    cv2.line(img, p1, p2, (0, 255, 255), 2)
    return p1, p2


def getDigitFromImage(im):
    from sklearn.externals import joblib
    from skimage.feature import hog

    # Load the classifier
    digits_cls = os.path.join(os.path.dirname(__file__), 'res/digits_cls.pkl')
    # clf, pp = joblib.load('res/digits_cls.pkl')
    clf, pp = joblib.load(digits_cls)

    # im_gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    im_gray = im

    # Threshold the image
    ret, im_th = cv2.threshold(im_gray, 3, 5, cv2.THRESH_BINARY_INV)

    # Find contours in the image
    # ctrs, hier = cv2.findContours(im_gray.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    ret, im_th_inv = cv2.threshold(im_gray, 10, 50, cv2.THRESH_BINARY_INV)

    used_img = im_th_inv

    cv2.imshow('used_img', used_img)

    ctrs, hier = cv2.findContours(used_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Get rectangles contains each contour
    rects = [cv2.boundingRect(ctr) for ctr in ctrs]

    # For each rectangular region, calculate HOG features and predict
    # the digit using Linear SVM.
    for ctr in ctrs:
        rect = cv2.boundingRect(ctr)
        x, y, w, h = cv2.boundingRect(ctr)
        if h > w and h > (digitheight * 4) / 5:
            # Draw the rectangles
            cv2.rectangle(used_img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (255, 0, 0), 1)
            # Make the rectangular region around the digit
            leng = int(rect[3] * 1.6)
            pt1 = int(rect[1] + rect[3] // 2 - leng // 2)
            pt2 = int(rect[0] + rect[2] // 2 - leng // 2)
            roi = im_th[pt1:pt1 + leng, pt2:pt2 + leng]
            # Resize the image
            roi = cv2.resize(roi, (28, 28), interpolation=cv2.INTER_AREA)
            roi = cv2.dilate(roi, (3, 3))
            # Calculate the HOG features
            roi_hog_fd = hog(roi, orientations=9, pixels_per_cell=(14, 14), cells_per_block=(1, 1))
            roi_hog_fd = pp.transform(np.array([roi_hog_fd], 'float64'))
            nbr = clf.predict(roi_hog_fd)
            cv2.putText(used_img, str(int(nbr[0])), (rect[0], rect[1]), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 255, 255), 3)
            print 'main digit: ' + str(int(nbr[0]))
    cv2.imshow('digit detect', used_img)


def get_line_coord_perpendicular(p1, p2, dist, first=True):
    x1 = float(p1[0])
    y1 = float(p1[1])

    x2 = float(p2[0])
    y2 = float(p2[1])

    if first:
        x = x1
        y = y1

    else:
        x = x2
        y = y2

    k, b = get_line_param(p1, p2)

    y_new = int(y + dist)
    x_new = int(k * (y - y_new) + x)
    return x_new, y_new


def getRandomString(size=6):
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def rotate(image, angle, center=None, scale=1.0):
    (h, w) = image.shape[:2]

    if center is None:
        center = (w / 2, h / 2)

    # Perform the rotation
    M = cv2.getRotationMatrix2D(center, angle, scale)
    rotated = cv2.warpAffine(image, M, (w, h))

    return rotated


def drawMatches(img1, kp1, img2, kp2, matches):
    """
    My own implementation of cv2.drawMatches as OpenCV 2.4.9
    does not have this function available but it's supported in
    OpenCV 3.0.0

    This function takes in two images with their associated
    keypoints, as well as a list of DMatch data structure (matches)
    that contains which keypoints matched in which images.

    An image will be produced where a montage is shown with
    the first image followed by the second image beside it.

    Keypoints are delineated with circles, while lines are connected
    between matching keypoints.

    img1,img2 - Grayscale images
    kp1,kp2 - Detected list of keypoints through any of the OpenCV keypoint
              detection algorithms
    matches - A list of matches of corresponding keypoints through any
              OpenCV keypoint matching algorithm
    """

    # Create a new output image that concatenates the two images together
    # (a.k.a) a montage
    rows1 = img1.shape[0]
    cols1 = img1.shape[1]
    rows2 = img2.shape[0]
    cols2 = img2.shape[1]

    out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')

    # Place the first image to the left
    out[:rows1, :cols1] = np.dstack([img1, img1, img1])

    # Place the next image to the right of it
    out[:rows2, cols1:] = np.dstack([img2, img2, img2])

    # For each pair of points we have between both images
    # draw circles, then connect a line between them
    for mat in matches:
        # Get the matching keypoints for each of the images
        img1_idx = mat.queryIdx
        img2_idx = mat.trainIdx

        # x - columns
        # y - rows
        (x1, y1) = kp1[img1_idx].pt
        (x2, y2) = kp2[img2_idx].pt

        # Draw a small circle at both co-ordinates
        # radius 4
        # colour blue
        # thickness = 1
        cv2.circle(out, (int(x1), int(y1)), 4, (255, 0, 0), 1)
        cv2.circle(out, (int(x2) + cols1, int(y2)), 4, (255, 0, 0), 1)

        # Draw a line in between the two points
        # thickness = 1
        # colour blue
        cv2.line(out, (int(x1), int(y1)), (int(x2) + cols1, int(y2)), (255, 0, 0), 1)

    # Show the image
    cv2.namedWindow('Features', cv2.WINDOW_NORMAL)
    cv2.imshow('Features', out)
    cv2.waitKey(0)
    cv2.destroyWindow('Matched Features')

    # Also return the image if you'd like a copy
    return out


def findCoordStartEndBracket(img, img_bracket_middle, img_start_bracket, point_1, point_2):
    w, h = img_bracket_middle.shape[::-1]
    # Crop from x, y, w, h

    add_y_min = point_1[1] - h
    add_y_max = point_1[1] + h

    start_x = point_1[0]
    add_x = point_1[0]
    counter = 0
    stop = False
    while add_x > 0 and not stop:
        new_point_1 = (start_x, add_y_min)
        new_point_2 = (add_x - w, add_y_max)
        cropped = img[
                  new_point_1[1]:new_point_2[1],
                  new_point_2[0]:new_point_1[0]
                  ]
        # cv2.imshow('cropped', cropped)
        # cv2.waitKey(0)

        find_pos = MultiScaleSearchTemplate(cropped, img_start_bracket)
        print find_pos[0], find_pos[1], counter
        stop = find_pos[0]
        if stop:
            cv2.rectangle(img, new_point_1, new_point_2, (0, 0, 255), 2)

        add_x -= w / 2
        counter += 1


def MultiScaleSearchTemplate(img, template):
    import imutils
    location = False
    found = False
    w_img, h_img = img.shape[::-1]

    for scale in np.linspace(0.7, 1.7, 30)[::-1]:
        # print scale, found
        if found:
            break
        resize_template = imutils.resize(template, width=int(template.shape[1] * scale))

        # cv2.imshow('img_edges', img_edges)
        # cv2.imshow('template_edges', template_edges)
        # cv2.waitKey(0)
        w, h = resize_template.shape[::-1]
        if w_img < w or h_img < h:
            continue

        thresh_template = cv2.threshold(resize_template, 0, 255,
                                        cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        thresh_img = cv2.threshold(img, 0, 255,
                                   cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

        # kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 5))
        # thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        cv2.namedWindow('thresh', cv2.WINDOW_NORMAL)
        # cv2.imshow('thresh', thresh_img)
        cv2.imshow('thresh', thresh_template)
        # cv2.waitKey(0)

        # result = cv2.matchTemplate(img, resize_template, cv2.TM_CCOEFF_NORMED)
        result = cv2.matchTemplate(thresh_img, thresh_template, cv2.TM_CCOEFF_NORMED)

        threshold = 0.75
        loc = np.where(result >= threshold)
        for pt in zip(*loc[::-1]):
            bound_1 = pt
            bound_2 = (pt[0] + w, pt[1] + h)
            cv2.rectangle(img, bound_1, bound_2, (0, 0, 255), 2)
            location = (bound_1, bound_2)
            # print location
            found = True
            break

    return found, location

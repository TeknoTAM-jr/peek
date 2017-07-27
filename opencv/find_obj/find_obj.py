#!/usr/bin/env python

''' From docs:
Feature-based image matching sample.

USAGE
  find_obj.py [--feature=<sift|surf|orb>[-flann]] [ <image1> <image2> ]

  --feature  - Feature to use. Can be sift, surf of orb. Append '-flann' to feature name
				to use Flann-based matcher instead bruteforce.

'''

# Goal: 
# Input: control and query image
# Output: aligned and cropped query image

import numpy as np
import cv2
import sys, getopt

FLANN_INDEX_KDTREE = 1  # bug: flann enums are missing
FLANN_INDEX_LSH    = 6

def get_detector_and_matcher(feature_name):
	chunks = feature_name.split('-')
	if chunks[0] == 'sift':
		detector = cv2.SIFT()
		norm = cv2.NORM_L2
	elif chunks[0] == 'surf':
		detector = cv2.SURF(800)
		norm = cv2.NORM_L2
	elif chunks[0] == 'orb':
		detector = cv2.ORB(400)
		norm = cv2.NORM_HAMMING
	else:
		return None, None
	if 'flann' in chunks:
		if norm == cv2.NORM_L2:
			flann_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
		else:
			flann_params= dict(algorithm = FLANN_INDEX_LSH,
							   table_number = 6, # 12
							   key_size = 12,     # 20
							   multi_probe_level = 1) #2
		# bug : need to pass empty dict (#1329)
		matcher = cv2.FlannBasedMatcher(flann_params, {})
	else:
		matcher = cv2.BFMatcher(norm)
	return detector, matcher


def filter_matches(kp1, kp2, matches, ratio=0.75):
	# matched key points
	mkp1, mkp2 = [], []
	for m in matches:
		if len(m) == 2 and m[0].distance < m[1].distance * ratio:
			m = m[0]
			mkp1.append( kp1[m.queryIdx] )
			mkp2.append( kp2[m.trainIdx] )
	p1 = np.float32([kp.pt for kp in mkp1])
	p2 = np.float32([kp.pt for kp in mkp2])
	kp_pairs = zip(mkp1, mkp2)
	return p1, p2, kp_pairs


def draw_match(window, img1, img2, kp_pairs, status=None, H=None):
	h1, w1 = img1.shape[:2]
	h2, w2 = img2.shape[:2]
	vis = np.zeros((max(h1, h2), w1+w2), np.uint8)
	vis[:h1, :w1] = img1
	vis[:h2, w1:w1+w2] = img2
	vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)

	if H is not None:
		corners = np.float32([[0, 0], [w1, 0], [w1, h1], [0, h1]])
		corners = np.int32( cv2.perspectiveTransform(corners.reshape(1, -1, 2), H).reshape(-1, 2) + (w1, 0) )
		cv2.polylines(vis, [corners], True, (255, 255, 255))

	if status is None:
		status = np.ones(len(kp_pairs), np.bool_)
	p1 = np.int32([kpp[0].pt for kpp in kp_pairs])
	p2 = np.int32([kpp[1].pt for kpp in kp_pairs]) + (w1, 0)

	green = (0, 255, 0)
	red = (0, 0, 255)
	white = (255, 255, 255)
	kp_color = (51, 103, 236)
	for (x1, y1), (x2, y2), inlier in zip(p1, p2, status):
		if inlier:
			col = green
			cv2.circle(vis, (x1, y1), 2, col, -1)
			cv2.circle(vis, (x2, y2), 2, col, -1)
		else:
			col = red
			r = 2
			thickness = 3
			cv2.line(vis, (x1-r, y1-r), (x1+r, y1+r), col, thickness)
			cv2.line(vis, (x1-r, y1+r), (x1+r, y1-r), col, thickness)
			cv2.line(vis, (x2-r, y2-r), (x2+r, y2+r), col, thickness)
			cv2.line(vis, (x2-r, y2+r), (x2+r, y2-r), col, thickness)
	vis0 = vis.copy()
	for (x1, y1), (x2, y2), inlier in zip(p1, p2, status):
		if inlier:
			cv2.line(vis, (x1, y1), (x2, y2), green)
	cv2.imshow(window, vis)


def match_and_draw(window):
	print 'matching...'
	raw_matches = matcher.knnMatch(desc1, trainDescriptors = desc2, k = 2) #2
	p1, p2, kp_pairs = filter_matches(kp1, kp2, raw_matches)
	if len(p1) >= 4:
		# H: ???
		# status: ???
		H, status = cv2.findHomography(p1, p2, cv2.RANSAC, 5.0)
		print '%d / %d  inliers/matched' % (np.sum(status), len(status))
	else:
		H, status = None, None
		print '%d matches found, not enough for homography estimation' % len(p1)
	
	print kp_pairs[0]
	draw_match(window, img1, img2, kp_pairs, status, H)


def parse_args():
	opts, args = getopt.getopt(sys.argv[1:], '', ['feature='])
	opts = dict(opts)
	feature_name = opts.get('--feature', 'sift')
	try:
		fn1, fn2 = args
	except:
		fn1 = 'control.jpg'
		fn2 = 'rotated.jpg'
	return fn1, fn2, feature_name


if __name__ == '__main__':
	fn1, fn2, feature_name = parse_args()
	img1 = cv2.imread(fn1, 0)
	img2 = cv2.imread(fn2, 0)

	detector, matcher = get_detector_and_matcher(feature_name)
	print 'using', feature_name if detector != None else sys.exit(1)		

	kp1, desc1 = detector.detectAndCompute(img1, None)
	kp2, desc2 = detector.detectAndCompute(img2, None)
	print "img1 - %d features" % len(kp1)
	print "img2 - %d features" % len(kp2)

	match_and_draw('find_obj')
	cv2.waitKey()
	cv2.destroyAllWindows()

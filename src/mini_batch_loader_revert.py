#!/usr/bin/env python2.7
# coding:utf-8
 
import os
import numpy as np
import cv2
import cPickle
import math
import time
 
class MiniBatchLoader(object):
 
    def __init__(self, args):
 
        # load data paths
        self.data_dir = args.img_dir
        self.mean = np.array([113.970, 110.130, 103.804])
        self.in_size = args.inputRes
        self.outRes = args.outputRes
        self.classes = args.n_joints
 
    # test ok
    def load_data(self, line, flip):
        in_channels = 3
        xs = np.zeros((1, in_channels,  self.in_size, self.in_size)).astype(np.float32)
        ys = np.zeros((1, self.classes, self.outRes, self.outRes)).astype(np.float32)

        datum = line.split(',')
        img_fn = '%s%s' % (self.data_dir, datum[0])
        
        #_/_/_/ xs: read image & joint _/_/_/  
        img = cv2.imread(img_fn) 
        h, w, _ = img.shape

        if flip:
            img = np.fliplr(img)

        l = max(w,h)
        cx = w/2
        cy = h/2
        x = cx - l/2
        y = cy - l/2

        crop = [x, y, l, l]

        pad = l
        img = np.pad(img, ((pad,pad),(pad,pad),(0,0)), 'constant')
        x += pad
        y += pad

        img = img[y:y + l, x:x + l]

        #_/_/_/ resize _/_/_/
        orig_h, orig_w, _ = img.shape
        img = cv2.resize(img, (self.in_size, self.in_size),interpolation=cv2.INTER_CUBIC)

        xs[0, :, :, :] = ((img - self.mean)/255).transpose(2, 0, 1)           

        return xs, ys, crop


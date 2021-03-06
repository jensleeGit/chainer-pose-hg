#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import cPickle as pickle
from mini_batch_loader_revert import MiniBatchLoader
from chainer import serializers
from hourglass import Hourglass
from chainer import cuda, optimizers, Variable
import sys
import numpy as np
import scipy.io as sio
import cv2
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--img_dir', type=str, default="data/LSP/images/")
    parser.add_argument('--test_csv_fn', type=str, default="data/LSP/test_joints.csv")
    parser.add_argument('--result_dir', type=str, default="result_img/")
    parser.add_argument('--weight_path', type=str, default='result/LSP/1/epoch_40.model')
    parser.add_argument('--n_joints', type=int, default=16)
    parser.add_argument('--inputRes', type=int, default=256)
    parser.add_argument('--outputRes', type=int, default=64)
    args = parser.parse_args()
    
    test_dl = np.array([l.strip() for l in open(args.test_csv_fn).readlines()])

    mini_batch_loader = MiniBatchLoader(args)

    # get model
    hourglass = pickle.load(open(args.weight_path, 'rb'))
    hourglass = hourglass.to_gpu()

    sum_accuracy = 0
    sum_loss     = 0
    test_data_size = len(test_dl)
    ests = np.zeros((test_data_size, args.n_joints, 2)).astype(np.float32)
    pool = np.zeros((2, args.n_joints, 2)).astype(np.float32)

    for i in range(0, test_data_size):
        sys.stdout.write('img  '+str(i)+'\r')
        sys.stdout.flush()
        for flip in [0,1]:
            raw_x, raw_t, crop = mini_batch_loader.load_data(test_dl[i], flip)
            x = Variable(cuda.to_gpu(raw_x))
            t = Variable(cuda.to_gpu(raw_t))
            hourglass.train = False
            pred = hourglass(x, t)
            sum_loss     += hourglass.loss.data

            #_/_/_/ max location _/_/_/
            hmap = cuda.to_cpu(pred.data[0])
            joints = np.zeros((args.n_joints,2))
            for j in range(args.n_joints):
                one_joint_map = hmap[j+args.n_joints,:,:]
                maxi = np.argmax(one_joint_map)
                joints[j,:] = np.unravel_index(maxi,(args.outputRes,args.outputRes))

            joints[:,[0,1]] = joints[:,[1,0]]  # Because unravel_index return (row, column), so tranfer to (x,y)
            joints[:,0] = joints[:,0] * crop[3] / args.outputRes
            joints[:,1] = joints[:,1] * crop[2] / args.outputRes
            joints[:,0] = joints[:,0] + crop[0]
            joints[:,1] = joints[:,1] + crop[1]

            if flip:
                img = cv2.imread(args.img_dir+test_dl[i].split(',')[0])
                joints[:,0] = img.shape[1] - joints[:,0]
                joints = list(zip(joints[:,0], joints[:,1]))

                joints[0], joints[5] = joints[5], joints[0] #ankle
                joints[1], joints[4] = joints[4], joints[1] #knee
                joints[2], joints[3] = joints[3], joints[2] #hip
                joints[6], joints[11] = joints[11], joints[6] #wrist
                joints[7], joints[10] = joints[10], joints[7] #elbow
                joints[8], joints[9] = joints[9], joints[8] #shoulder

                joints = np.array(joints).flatten()
                joints = joints.reshape((len(joints) / 2, 2))

            pool[flip,:,:] = joints

        ests[i,:,:] = np.sum(pool,axis=0) / 2

        img = cv2.imread(args.img_dir+test_dl[i].split(',')[0])
        joints = joints.astype(np.int32)
        joints = [tuple(p) for p in joints]
        for j, joint in enumerate(joints):
            cv2.putText(img, '%d' % j, joint, cv2.FONT_HERSHEY_SIMPLEX, 0.3,(255, 255, 255))
            cv2.circle(img, joint, 2, (0, 0, 255), -1)
        cv2.imwrite(args.result_dir+str(i)+'.jpg',img)
        

    sio.savemat(args.result_dir+'ests.mat', {'ests':ests})

    sys.stdout.flush()

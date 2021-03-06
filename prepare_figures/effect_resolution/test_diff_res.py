#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 11 22:05:12 2018

@author: ajaver
"""

from tierpsy.helper.params import read_microns_per_pixel
import pandas as pd
import tables
import glob
import os
import numpy as np

import matplotlib.pylab as plt

#fname = '/Users/ajaver/OneDrive - Imperial College London/aggregation/N2_1_Ch1_29062017_182108_comp3.hdf5'
#print(read_microns_per_pixel(fname))
#
#fname = '/Users/ajaver/OneDrive - Imperial College London/Ev_videos/N2_adults/MaskedVideos/N2_A_24C_L_5_2015_06_16__19_54_27__.hdf5'
#print(read_microns_per_pixel(fname))

main_dir = '/Users/ajaver/OneDrive - Imperial College London/Ev_videos/diff_resolutions/Results'
#fnames = glob.glob(os.path.join(main_dir, '*_features.hdf5'))

#ext_s = '_featuresN.hdf5'
ext_s = '_features.hdf5'
field_n = '/features_timeseries'

fnames = glob.glob(os.path.join(main_dir, '*' + ext_s))

#%%
plt.figure()
feats = {}
masks = {}
bn_k = {'N2_45':'45x34',
        'N2_91':'91x68',
        'N2_213':'213x160',
        'N2_640':'640x480'
        }

scale_k = {}

for fname in fnames:
    bn = os.path.basename(fname)
    bn = bn.replace(ext_s, '')
    with pd.HDFStore(fname, 'r') as fid:
        if not bn in bn_k:
            continue
        
        #feats[bn] = fid['/timeseries_data']
        if field_n in fid:
            feats[bn_k[bn]] = fid[field_n]
    
    f_skel = fname.replace(ext_s, '_skeletons.hdf5')
    if os.path.exists(f_skel):
        with tables.File(f_skel, 'r') as fid:
            skel = fid.get_node('/skeleton')[0]
    else:
        skel = None

    ff = fname.replace(ext_s, '.hdf5').replace('Results', 'MaskedVideos')
    with tables.File(ff, 'r') as fid:
        img = fid.get_node('/full_data')[0]
        microns_per_pixel = read_microns_per_pixel(ff)
        
    masks[bn_k[bn]] = (microns_per_pixel, img, skel)

#%%
#plt.figure(figsize = (12, 5))

fig, axs = plt.subplots(1, 4, figsize = (12, 4))

bgnd_pix = 187
ll = ['45x34', '91x68', '213x160', '640x480'][::-1]

l_scale_mu = 500
for i_k, k in enumerate(ll):
    (microns_per_pixel, img, skel) = masks[k]
    pix = int(k.split('x')[0])
    l_scale = l_scale_mu/microns_per_pixel
    
    n_scale = pix/640
    x_cc = 450*n_scale
    y_cc = 450*n_scale
    
    
    sc_t = '{:.1f} $\mu$m/pix'.format(microns_per_pixel)
    strT = '{}\n{}'.format(sc_t, k)
    
    img_c = img.copy()
    img_c[img_c==0] = bgnd_pix
    
    #plt.subplot(1, 4, i_k+1)
    axs[i_k].imshow(img_c, interpolation=None, cmap='gray', vmin=0, vmax=img_c.max())
    
    
    
    if i_k == 3:
        axs[i_k].text(x_cc, y_cc, str(l_scale_mu) + '$\mu$m', fontsize=11, va='bottom', ha='left')
        axs[i_k].plot((x_cc, x_cc+l_scale), (y_cc,y_cc), 'k', linewidth=  3)
    
    if skel is not None:
        axs[i_k].plot(skel[:, 0], skel[:, 1], 'r', lw=2)
    
    
    
    axs[i_k].text(0, 350*n_scale, strT, fontsize=12, verticalalignment='top')
    
    axs[i_k].axis('off')
    
    scale_k[k] = sc_t
    
plt.subplots_adjust(wspace=0.01)
plt.savefig('scales.pdf', bbox_inches='tight')

#%%
cols = ['length', 'foraging_speed', 'midbody_speed', 
        'head_bend_mean']

units = ['Length\n[$\mu$m]',
         'Foraging\nSpeed[deg/s]', 
         'Midbody Speed\n[$\mu$m/s]', 
         'Mean Head\nBend [deg]'
         ]


valid_keys = ['91x68', '213x160', '640x480']
    
tot_feats = len(cols)

f, axs_ts = plt.subplots(tot_feats, 1, figsize=(7, 7), sharex=True)
for icol, col in enumerate(cols):  
    for ii, bn in enumerate(valid_keys):
        #plt.subplot(3,1, ii + 1)
        x = feats[bn]['timestamp'].values/25
        y = feats[bn][col].values
        axs_ts[icol].plot(x, y, lw = 1.5)
        
    axs_ts[icol].set_ylabel(units[icol], fontsize=13)
    axs_ts[icol].get_yaxis().set_label_coords(-0.08,0.5)
    axs_ts[icol].tick_params(axis='both', which='major', labelsize=10, direction='in')
    

plt.xlim([200, 275])
plt.xlabel('Time [s]', fontsize=13)

plt.tight_layout()
plt.subplots_adjust(hspace=0.02) 
plt.savefig('ts.pdf'.format(col))
#%%

fig, axs_h = plt.subplots(tot_feats, 1, figsize=(3, 7), sharex=True, sharey=False)

for icol, col in enumerate(cols):  
    top = max(tab[col].max() for tab in feats.values())
    bot = min(tab[col].min() for tab in feats.values())
    #plt.figure(figsize=(3, 3))
    
    #plt.subplot(tot_feats, 1, icol+1)
    for bn in valid_keys:
        cc, bin_edges = np.histogram(feats[bn][col].dropna(), bins=100, range =(bot, top))
        
        xx = cc
        yy = bin_edges[1:]
        axs_h[icol].plot(xx, yy, label=scale_k[bn], lw = 2)
        axs_h[icol].fill(xx, yy, alpha=0.1)
        axs_h[icol].tick_params(axis='y', labelleft='off')
        #axs_h[icol].set_xticks([])
    #u_s = units[icol].replace('\n', ' ')
    #axs_h[icol].set_xlabel(u_s)
    
#plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
axs_h[-1].set_xlabel('Counts', fontsize=13)
axs_h[-1].set_xlim(0, 800)
axs_h[-1].legend(fontsize=13)

plt.tight_layout()
plt.subplots_adjust(hspace=0.02)
plt.savefig('hist.pdf'.format(col))

#%%
if False:
    #f, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True, sharex=True)
    #plt.subplot(1,2,2)
    xx = feats['640x480'][col]
    for ii, bn in enumerate(['91x68', '213x160']):
        plt.plot(xx, feats[bn][col], '.', label=scale_k[bn])
        plt.xlabel('640x480')
        #plt.ylabel(bn)
    
    plt.suptitle(col)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('{}_hist.pdf'.format(col))
    #%%

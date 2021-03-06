#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 20 18:35:13 2017

@author: ajaver
"""
import tables
import numpy as np
import pandas as pd
import os
from scipy.io import loadmat

from tierpsy.analysis.stage_aligment.alignStageMotion import _h_get_stage_inv

tab_path = os.path.join(os.path.dirname(__file__), 'conversion_table.csv')
feats_conv = pd.read_csv(tab_path).dropna()
FEATS_MAT_MAP = {row['feat_name_tierpsy']:row['feat_name_segworm'] for ii, row in feats_conv.iterrows()}
FEATS_OW_MAP = {row['feat_name_tierpsy']:row['feat_name_openworm'] for ii, row in feats_conv.iterrows()}

def test_mismatching():
    for x in FEATS_MAT_MAP:
        mat = FEATS_MAT_MAP[x]
        ow = FEATS_OW_MAP[x]
        
        mat_r = mat.replace('/worm/', '').replace('/','.')
        if mat_r != ow:
            d1 = mat_r.split('.')
            d2 = ow.split('.')
            
            missed = [x for x in d1 if not x in d2]
            
            
            print(missed, ow, mat)

class FeatsReader():
    def __init__(self, feat_file):
        self.feat_file = feat_file
    
    @property
    def features_events(self):
        try:
            return self._features_events
        except:
            with tables.File(self.feat_file, 'r') as fid:
            
                features_events = {}
                node = fid.get_node('/features_events')
                for worn_n in node._v_children.keys():
                    worm_node = fid.get_node('/features_events/' + worn_n)
                    
                    for feat in worm_node._v_children.keys():
                        if not feat in features_events:
                            features_events[feat] = {}
                        dat = fid.get_node(worm_node._v_pathname, feat)[:]
                        features_events[feat][worn_n] = dat
            
            
            self._features_events = features_events
            return self._features_events
    
    @property
    def features_events_plate(self):
        def dict2array(dd):
            return np.concatenate([val for val in dd.values()])
        return {feat:dict2array(val) for feat, val in self.features_events.items()}
    
    @property
    def features_timeseries(self):
        try:
            return self._features_timeseries
        except:
            with pd.HDFStore(self.feat_file, 'r') as fid:
                self._features_timeseries = fid['/features_timeseries']
            return self._features_timeseries
    
    
    def read_plate_features(self):
        dd = {x:self.features_timeseries[x].values for x in self.features_timeseries}
        worm_features_dict = {**dd, **self.features_events_plate}
        return worm_features_dict
    
    def get_worm_coord(self, worm_index, field_name):
        good_rows = self.features_timeseries['worm_index'] == worm_index
        rows_indexes = good_rows.index.values[good_rows.values]
    
        with tables.File(self.feat_file, 'r') as fid:
            skeletons = fid.get_node('/coordinates/' + field_name)[rows_indexes, : , :]
        
        #shift to correct using the timestamp
        inds = self.features_timeseries.loc[rows_indexes, 'timestamp'].astype(np.int)
        tot = inds.max() + 1
        
        #import pdb
        #pdb.set_trace()
        
        if tot != skeletons.shape[0]:
            skeletons_ts = np.full((tot, *skeletons.shape[1:]), np.nan)
            skeletons_ts[inds] = skeletons
            return skeletons_ts
        else:
            return skeletons
   
    
    
class FeatsReaderComp(FeatsReader): 
    def __init__(self, feat_file, segworm_feat_file='', skel_file=''):
        if not segworm_feat_file:
            segworm_feat_file = feat_file.replace('.hdf5', '.mat')
        
        if not skel_file:
            skel_file = feat_file.replace('_features.hdf5', '_skeletons.hdf5')
        
        self.skel_file = skel_file
        self.segworm_feat_file = segworm_feat_file
        super().__init__(feat_file)
    
    def _read_feats_segworm_hdf5(self):
        with tables.File(self.segworm_feat_file, 'r') as fid: 
            feats_segworm = {}
            for name_tierpsy, name_segworm in FEATS_MAT_MAP.items():
                if name_segworm in fid:           
                    if not 'eigenProjection' in name_segworm:
                        dd = fid.get_node(name_segworm)
                        if dd != np.dtype('O'):
                            feats_segworm[name_tierpsy] = dd[:]
                        else:
                            if len(dd) == 1:
                                dd = dd[0]
                            feats_segworm[name_tierpsy]=np.array([x[0][0,0] for x in dd])
                            
                    else:
                        ii = int(name_tierpsy.replace('eigen_projection_', '')) - 1
                        feats_segworm[name_tierpsy] = fid.get_node(name_segworm)[:, ii]
                else:
                    feats_segworm[name_tierpsy] = np.array([np.nan])
            
            for key, val in feats_segworm.items():
                feats_segworm[key] = np.squeeze(val)
        
        
        return feats_segworm
    
    def _read_feats_segworm_mat(self):
        dat  = loadmat(self.segworm_feat_file)
        feats_segworm = {}
        for name_tierpsy, name_segworm in FEATS_MAT_MAP.items():
            prev = dat
            for field in name_segworm.split('/'):
                
                if isinstance(prev, (np.ndarray, np.void)):
                    
                    ff = prev.dtype.names
                    if not ff is None:
                        has_field = field in ff
                    else:
                        has_field = False
                else:
                    has_field = field in prev
                
                if has_field:
                    prev = prev[field]
                    if prev.size == 1 and prev.shape == (1,1):
                       prev = prev[0,0]
                
#                if name_tierpsy == 'inter_backward_distance':
#                    print(field)
#                    import pdb
#                    pdb.set_trace()
                        
            
            
            if 'eigen_projection_' in name_tierpsy:
                ii = int(name_tierpsy.replace('eigen_projection_', '')) - 1
                prev = prev[ii, :]
                
            if isinstance(prev, (np.float64, float)):
                prev = np.atleast_1d(np.array(prev))
            elif isinstance(prev, np.ndarray):
                prev = np.squeeze(prev)
                if prev.size == 0:
                    prev = np.nan
                elif prev.dtype == np.dtype('O'):
                    prev = prev.astype(np.float)
                else:
                    if prev.size < 100:
                        raise ValueError
                
                    
            feats_segworm[name_tierpsy] = prev
            
        return feats_segworm
    

    def read_feats_segworm(self):
        try:
            feats_segworm = self._read_feats_segworm_hdf5()
        except:
            feats_segworm = self._read_feats_segworm_mat()
        
        return feats_segworm

    def _read_skels_segworm_hdf5(self):
        with tables.File(self.segworm_feat_file, 'r') as fid:
            segworm_x = fid.get_node('/worm/posture/skeleton/x')[:]
            segworm_y = fid.get_node('/worm/posture/skeleton/y')[:]
        return segworm_x, segworm_y
        
    
    def read_skels_segworm_mat(self):
        dat  = loadmat(self.segworm_feat_file)
        segworm_x = dat['worm'][0,0]['posture'][0,0]['skeleton'][0,0]['x']
        segworm_y = dat['worm'][0,0]['posture'][0,0]['skeleton'][0,0]['y']
        
        return segworm_x.T, segworm_y.T

    @property
    def skels_segworm(self):
        try:
            return self._skels_segworm
        except:
            #load segworm data
            try:
                segworm_x, segworm_y = self._read_skels_segworm_hdf5()
            except:
                segworm_x, segworm_y = self.read_skels_segworm_mat()
            
            skel_segworm = np.stack((-segworm_x,-segworm_y), axis=2)
            skel_segworm = np.rollaxis(skel_segworm, 0, skel_segworm.ndim)
            skel_segworm = np.asfortranarray(skel_segworm)
            
            self._skels_segworm = np.rollaxis(skel_segworm, 2, 0)
            
            return self._skels_segworm
    
    @property
    def skeletons(self):
        try:
            return self._skeletons
        except:
            #load segworm data
            self._skeletons = self.get_worm_coord(1, 'skeletons')
            return self._skeletons


    def read_skeletons(self):
        return self._align_skeletons(self.skel_file, self.skeletons, self.skels_segworm)
    
    def _align_skeletons(self, skel_file, skeletons, skel_segworm):
            #load rotation matrix to compare with the segworm
            with tables.File(skel_file, 'r') as fid:
                rotation_matrix = fid.get_node('/stage_movement')._v_attrs['rotation_matrix']
            
            
                microns_per_pixel_scale = fid.get_node(
                        '/stage_movement')._v_attrs['microns_per_pixel_scale']
            
            # rotate skeleton to compensate for camera movement
            dd = np.sign(microns_per_pixel_scale)
            rotation_matrix_inv = np.dot(
                rotation_matrix * [(1, -1), (-1, 1)], [(dd[0], 0), (0, dd[1])])
            for tt in range(skel_segworm.shape[0]):
                skel_segworm[tt] = np.dot(rotation_matrix_inv, skel_segworm[tt].T).T
        
            max_n_skel = min(skel_segworm.shape[0], skeletons.shape[0])
            #shift the skeletons coordinate system to one that diminushes the errors the most.
            dskel = skeletons[:max_n_skel]-skel_segworm[:max_n_skel]
            seg_shift = np.nanmedian(dskel, axis = (0,1))
            skel_segworm += seg_shift
            
            return skeletons, skel_segworm

    @property
    def stage_movement(self):
        try:
            return self._stage_movement
        except:
            timestamp = np.arange(self._skeletons.shape[0])
            self._stage_movement, _ = _h_get_stage_inv(self.skel_file, timestamp)
            return self._stage_movement


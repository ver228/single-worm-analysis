# -*- coding: utf-8 -*-
"""
Created on Wed Apr 27 16:17:35 2016

@author: ajaver
"""

import os
import tables
import pandas as pd
import numpy as np
import pymysql.cursors
import multiprocessing as mp

from collections import OrderedDict
from tierpsy.helper.misc import TimeCounter
from tierpsy.helper.params import read_unit_conversions



PROGRESS_TAB_FIELD = ['experiment_id', 'n_valid_frames', 'n_missing_frames', 
    'n_segmented_skeletons', 'n_filtered_skeletons', 'n_valid_skeletons', 
    'n_timestamps', 'first_skel_frame', 'last_skel_frame', 'fps', 'total_time',
    'mask_file_sizeMB', 'microns_per_pixel']

def get_progress_data(experiment_id, results_dir, base_name):
    
    mask_file = os.path.join(results_dir, base_name + '.hdf5')
    skeletons_file = os.path.join(results_dir, base_name + '_skeletons.hdf5')
    features_file = os.path.join(results_dir, base_name + '_features.hdf5')
        
    out = OrderedDict()
    for x in PROGRESS_TAB_FIELD:
        out[x] = None
    out['experiment_id'] = experiment_id
    
    try:
        out['mask_file_sizeMB'] =  os.path.getsize(mask_file)/(1024*1024.0)
        with tables.File(mask_file, 'r') as fid:
            out['n_valid_frames'] = int(fid.get_node('/mask').shape[0])
        
        fps_out, microns_per_pixel_out, _ = read_unit_conversions(mask_file, None)
        microns_per_pixel, xy_units = microns_per_pixel_out

        if xy_units != 'micrometers':
            microns_per_pixel = None
        
        out['microns_per_pixel'] = microns_per_pixel
        fps, _, time_units = fps_out        
        if time_units != 'seconds':
            fps = None
        
        if not fps is None:
            out['fps'] = float(fps)
            with tables.File(mask_file, 'r') as fid:
                timestamp_time = fid.get_node('/timestamp/time')[:]
                timestamp_ind = fid.get_node('/timestamp/raw')[:]
                
                #sometimes only the last frame is nan
                timestamp_ind = timestamp_ind[~np.isnan(timestamp_time)]
                timestamp_time = timestamp_time[~np.isnan(timestamp_time)]
                assert timestamp_ind.size == timestamp_time.size
                
                if timestamp_ind.size > 0:
                    out['n_missing_frames'] = int(timestamp_ind[-1] - out['n_valid_frames'] + 1)
                    out['total_time'] = float(timestamp_time[-1])
    except:
        pass
        
    try:
        with pd.HDFStore(skeletons_file, 'r') as fid:
            trajectories_data = fid['/trajectories_data']
            if len(trajectories_data) > 0:
                out['n_segmented_skeletons'] = int(trajectories_data['has_skeleton'].sum())
                out['first_skel_frame'] = int(trajectories_data['frame_number'].min())
                out['last_skel_frame'] = int(trajectories_data['frame_number'].max())
                if 'is_good_skel' in trajectories_data:
                    out['n_filtered_skeletons'] = int(trajectories_data['is_good_skel'].sum())
    except:
        pass
    
    try:
        with tables.File(features_file, 'r') as fid:
            if '/coordinates/skeletons' in fid:
                skel = fid.get_node('/coordinates/skeletons')[:,0,0] #use it as a proxy of valid skeletons
                if skel.size > 0:
                    out['n_valid_skeletons'] = int(np.sum(~np.isnan(skel)))
                    out['n_timestamps'] = len(skel)
                else:
                    out['n_valid_skeletons'] = 0
                    out['n_timestamps'] = 0
    except:
        pass
    
    return out

def update_row(row_input, table_name = 'results_summary'):
    names, values = zip(*list(row_input.items()))
    
    vals_str = []
    for x in values:
        if x is None:
            new_val = 'NULL'
        elif isinstance(x, str):
            new_val = '"{}"'.format(x)
        else:
            new_val = str(x)
        vals_str.append(new_val)
        
    values_str = ", ".join(vals_str)
    names_str = ", ".join("`{}`".format(x) for x in names)
    update_str = ", ".join('{}={}'.format(x, y) for x,y in zip(names,vals_str))
    
    sql = '''
    INSERT INTO `{}` ({}) 
    VALUES ({})    
    ON DUPLICATE KEY UPDATE {}
    '''.format(table_name, names_str, values_str, update_str)
    
    return sql
    
    
if __name__ == '__main__':
    conn = pymysql.connect(host='localhost', db='single_worm_db')
    cur = conn.cursor(pymysql.cursors.DictCursor)
    
    #sql = "SELECT id, results_dir, base_name FROM experiments"
    sql = "select id, results_dir, base_name from experiments where id not in (select experiment_id from results_summary);"
    cur.execute(sql)
    all_rows = cur.fetchall()
    
    def _process_row(row):
        results_dir = row['results_dir']
        base_name = row['base_name']
        
        
        
        row_progress = get_progress_data(row['id'], results_dir, base_name)
        return row_progress
    
    
    print('*******', len(all_rows))
    
    progress_timer = TimeCounter()
    n_batch = mp.cpu_count()
    p = mp.Pool(n_batch)
    tot = len(all_rows)
    for ii in range(0, tot, n_batch):
        dat = all_rows[ii:ii + n_batch]
        for x in p.map(_process_row, dat):
            #x = _process_row(x)
            if x is not None:
                sql = update_row(x)
                cur.execute(sql)
        conn.commit()
        print('{} of {}. Total time: {}'.format(min(tot, ii + n_batch), 
                  tot, progress_timer.get_time_str()))
    cur.close()
    conn.close()

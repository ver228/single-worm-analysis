#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 23 18:23:36 2018

@author: ajaver
"""
import numpy as np
import pandas as pd
import matplotlib.pylab as plt

import pymysql

if __name__ == '__main__':
    conn = pymysql.connect(host='localhost', db='single_worm_db')
    cur = conn.cursor()
    
    
    sql = '''
    select id from experiments_valid;
    '''
    cur.execute(sql)
    valid_exps = cur.fetchall()
    valid_exps, = zip(*valid_exps)
    
    #%%
    #data_file = '../../compare_segworm/all_skeletons_comparisons.hdf5'
    data_file = './all_skeletons_comparisons.hdf5'
    #this is large, maybe i cannot load it in memory in as small machine
    with pd.HDFStore(data_file, 'r') as fid:
        errors_data = fid['/data']
    #%%
    errors_data = errors_data[errors_data['experiment_id'].isin(valid_exps)]
    
    errors_data['RMSE_N'] = errors_data['RMSE']/errors_data['length_tierpsy']
    errors_data['RMSE_BEST_N'] = errors_data[['RMSE', 'RMSE_switched']].min(axis=1)/errors_data['length_tierpsy']
    
    #%%
    experiment_ids = errors_data['experiment_id'].unique()
    #%%
    err_n = errors_data['RMSE_N'].dropna()
    err_min_n =  errors_data['RMSE_BEST_N'].dropna()
    #%%
    ll = errors_data['RMSE'].dropna()
    rr = errors_data['RMSE_switched'].dropna()
    frac_th_switched = np.mean(ll>rr)
    print(frac_th_switched)
    
    #%%
    tot = err_n.size
    counts, bins = np.histogram(err_n, bins=1000, range = (0, 1))
    counts = counts/tot
    
    counts_min, bins = np.histogram(err_min_n, bins=1000, range = (0, 1))
    counts_min = counts_min/tot
    
    #%%
    def _get_switch_error(dat):
        delS = dd - dd[:, ::-1]
        R_error = np.sum(delS**2, axis=0)
        _switch_error = np.sqrt(np.mean(R_error))
        return _switch_error
    
    L = 1;
    dd = np.linspace(0, L, 49)
    dd = np.vstack((dd,dd))
    
    assert (1 -np.sum(np.sqrt(np.sum(np.diff(dd, axis=1)**2, axis=0)))) < 1e3
    
    switch_error_lin = _get_switch_error(dd)
    
    theta = np.linspace(np.pi, -np.pi, 49)
    
    L = 2*np.pi #normalize by circle length
    dd = np.vstack((np.sin(theta), np.cos(theta)))/L 
    
    assert (1 -np.sum(np.sqrt(np.sum(np.diff(dd, axis=1)**2, axis=0)))) < 1e3
    
    switch_error_circ = _get_switch_error(dd)
    
    
    #%%
    seg_size = 2/48
    
    
    
    #%%
    err_g = errors_data.dropna().groupby('experiment_id')
    #%%
    movie_fractions = []
    
    switch_th = 0.6
    for exp_id, dat in err_g:
        #print(exp_id)
        frac_good = (dat['RMSE_N'] <= seg_size).mean()
        frac_good_switched = (dat['RMSE_BEST_N'] <= seg_size).mean()
        
        #frac_switched = ((rmse_n > seg_size) & (rmse_n <= switch_th)).mean()
        frac_terrible = (dat['RMSE_BEST_N'] > switch_th).mean()
        
        movie_fractions.append((exp_id, frac_good, frac_good_switched, frac_terrible))
    
    exp_id, frac_good, frac_good_switched, frac_terrible = zip(*movie_fractions)
    dd = {'frac_good':frac_good, 'frac_good_switched':frac_good_switched, 'frac_terrible':frac_terrible}
    
    movie_fractions_df = pd.DataFrame(dd, index=exp_id)
    #%%
    plt.figure(figsize = (12, 5))
    
    plt.subplot(1,2,1)
    xx = bins[:-1] + (bins[1]-bins[0])/2
    yy = np.cumsum(counts)
    yy_m = np.cumsum(counts_min)
    
    #plt.figure(figsize=(8, 6))
    plt.plot(xx, yy, lw=3)
    plt.plot(xx, yy_m, lw=2)
    
    plt.plot((seg_size, seg_size), (-0.1, 1.1), ':r')
    #plt.plot((switch_error_lin, switch_error_lin), (-0.1, 1.1), ':r')
    #plt.plot((switch_error_circ, switch_error_circ), (-0.1, 1.1), ':r')
    
    plt.xlabel('RMSE / L')
    plt.ylabel('Cumulative P')
    plt.ylim((-0.025, 1.05))
    
    plt.subplot(1,2,2)
    vv = movie_fractions_df['frac_good'].sort_values()
    #plt.plot(np.linspace(0,1, vv.size), vv.values)
    plt.plot(vv.values)
    vv = movie_fractions_df['frac_good_switched'].sort_values()
    #plt.plot(np.linspace(0,1, vv.size), vv.values)
    plt.plot(vv.values)
    plt.xlabel('Movie Number')
    plt.ylabel('Fraction of (RMSE/L < 1/24)')
    
    dd = (movie_fractions_df[['frac_good', 'frac_good_switched']]>0.99).sum()
    plt.savefig('db_skel_comparison.pdf')
    
    
    #'95'
    #'8313 of 9343'
    #'#9299 of 9343'
    
    #%99.874 of frames have less than 1/24 
    #96.809 of frames less than 1/24
    #%3.08 frames switched
    #total skeletons 184117924
    
    
    #%%
    vv = movie_fractions_df['frac_terrible'].sort_values()
    #inds = (329, 3555,3556, 4231, 5124, 5991, 8759, 10407, 11260)
    conn = pymysql.connect(host='localhost', db='single_worm_db')
    cur = conn.cursor()
    
    
    ss = ','.join(['"{}"'.format(x) for x in inds])
    sql = '''
    select e.id, CONCAT(results_dir, '/', base_name, '.hdf5'), segworm_file
    from experiments as e 
    join segworm_info as s on e.id = s.experiment_id
    where e.id in ({});
    '''.format(ss)
    cur.execute(sql)
    bad_exps = cur.fetchall()
    
    for exp_id, fname, segname in bad_exps:
        print(exp_id)
        print(fname)
        print(segname)
    
    #[4787, 5247, 8881, 9107, 9117, 11307, 11600]
    
    # (329, 3555, 3556, 4231, 5124, 5991, 8759, 10407, 11260) , 647, 11109
    #%%
    #%%
    if False:
        '''
        This analysis is to try to get the fraction of good frames in each of the analys. However,
        it is tricky since this include the NaN's due to stage motions
        '''
        bad_in_segworm = errors_data[['length_segworm']].isnull()
        bad_in_tierpsy = errors_data[['length_tierpsy']].isnull()
        
        frac_bad_segworm = bad_in_segworm.mean()
        frac_bad_tierpsy = bad_in_tierpsy.mean()
        
        frac_bad_only_tierpsy = (bad_in_tierpsy.values & ~bad_in_segworm.values).mean()
        frac_bad_only_segworm = (~bad_in_tierpsy.values & bad_in_segworm.values).mean()
        
        err_g = errors_data.groupby('experiment_id')
        all_bad_frac = []
        for exp_id, dat in err_g:
            #print(exp_id)
            bad_in_tierpsy = dat[['length_tierpsy']].isnull()
            bad_in_segworm = dat[['length_segworm']].isnull()
            
            frac_bad_only_tierpsy = (bad_in_tierpsy.values & ~bad_in_segworm.values).mean()
            frac_bad_only_segworm = (~bad_in_tierpsy.values & bad_in_segworm.values).mean()
            
            all_bad_frac.append((exp_id, frac_bad_only_tierpsy, frac_bad_only_segworm))
        
        exp_id, frac_bad_only_tierpsy, frac_bad_only_segworm = zip(*all_bad_frac)
        
        dd = {'frac_bad_only_tierpsy':frac_bad_only_tierpsy, 'frac_bad_only_segworm':frac_bad_only_segworm}
        bad_frac_df = pd.DataFrame(dd, index = exp_id)
     
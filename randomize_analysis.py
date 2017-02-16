#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 17:45:43 2017

@author: ajaver
"""

import pymysql

conn = pymysql.connect(host='localhost', database='single_worm_db')
cur = conn.cursor()
sql = '''
select original_video 
from experiments_full 
where arena like '%liquid%' order by original_video_sizeMB'''

cur.execute(sql)
file_list = cur.fetchall()
file_list = [x for x, in file_list] #flatten

n_files = 2
divided_files = [[] for i in range(n_files)]
            

for ii, fname in enumerate(file_list):
    ind = ii % n_files
    divided_files[ind].append(fname)

for ii, f_list in enumerate(divided_files):
    with open('vid_swimming_{}.txt'.format(ii+1), 'w') as fid:
        fid.write('\n'.join(f_list))
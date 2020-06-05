# -*- coding: utf-8 -*-
"""
Created on Fri Jun  5 11:24:12 2020

@author: ihousman
"""
import ee,datetime
ee.Initialize()
def getDate(m):return datetime.datetime.fromtimestamp(float(m)/1000).strftime('%Y-%m-%d')

date = '2020-06-04'
######################################
x = ee.data.getTaskList()

ids = [i['description'] for i in x if i['description'].find('TDD_') > -1 and i['state'] == 'CANCELLED' and getDate(i['creation_timestamp_ms']) == date]
print(ids)
print(len(ids))
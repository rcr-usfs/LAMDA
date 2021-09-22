"""
   Copyright 2021 Ian Housman, RedCastle Resources Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
#Script to view LAMDA outputs
####################################################################################################
####################################################################################################
import  geeViz.geeView as geeView
ee = geeView.ee
Map = geeView.Map
from google.cloud import storage
import os,sys
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"Q:\RTFD_gee_method\credentials\gtac-rtfd-b50238099cd8.json"
#Clear any layers added to Map object
#If map is not cleared, layers are simply appended to the existing list of layers if layers have been added previously
Map.clearMap()
####################################################################################################
bucket = 'rtfd-delivery'

study_areas = ['CONUS','AK']
output_types = ['Z','TDD']


continuous_palette_chastain = ['a83800','ff5500','e0e0e0','a4ff73','38a800']
eight_bit_viz = {'min':0,'max':254,'palette':continuous_palette_chastain,'dateFormat':'YYYYMMdd','advanceInterval':'day'}
persistence_viz = {'min':0,'max':3,'palette':'e1e1e1,ffaa00,e10000,e100c5','dateFormat':'YYYYMMdd','advanceInterval':'day','classLegendDict':{'0 Detections':'e1e1e1','1 Detection':'ffaa00','2 Detections':'e10000','3 Detections':'e100c5'}}

def list_blobs(bucket_name):
    """Lists all the blobs in the bucket."""
    # bucket_name = "your-bucket-name"

    storage_client = storage.Client()

    # Note: Client.list_blobs requires at least package version 1.17.0.
    blobs = storage_client.list_blobs(bucket_name)
    return [i.name for i in blobs]
    # for blob in blobs:
    #     print(blob.name)

files = list_blobs(bucket)
tifs = [i for i in files if os.path.splitext(i)[1] == '.tif']

def getDate(name,jd_split_string = '_jd'):
  yr = int(name.split(jd_split_string)[0][-4:])
  day = int(name.split(jd_split_string)[1].split('-')[0])
  d = ee.Date.fromYMD(yr,1,1).advance(day-1,'day')
  return d.millis()
  # print(name,yr,day,d.format('YYYY-MM-dd').getInfo())
for study_area in study_areas:
  for output_type in output_types:
    tifsT = [i for i in tifs if i.find(study_area)>-1]
    tifsT = [i for i in tifsT if i.find(output_type)>-1]
    eight_bits= [i for i in tifsT if i.find('_8bit')>-1]
    persistence = [i for i in tifsT if i.find('_persistence')>-1]
    raws = [i for i in tifsT if i.find('_persistence')==-1 and i.find('_8bit')==-1]
    
    eight_bit_c = []
    for t in eight_bits:
      img = ee.Image.loadGeoTIFF('gs://{}/{}'.format(bucket,t))
      
      d = getDate(t)
      img = img.set('system:time_start',d)
      eight_bit_c.append(img)
    eight_bit_c = ee.ImageCollection(eight_bit_c)
    Map.addTimeLapse(eight_bit_c,eight_bit_viz,'{} {} 8 bit timelapse'.format(study_area,output_type),False)

    persistence_c = []
    print(persistence)
    for t in persistence:
      img = ee.Image.loadGeoTIFF('gs://{}/{}'.format(bucket,t))
      
      d = getDate(t,'_jds')
      img = img.set('system:time_start',d)
      persistence_c.append(img)
    persistence_c = ee.ImageCollection(persistence_c)
    Map.addTimeLapse(persistence_c,persistence_viz,'{} {} persistence timelapse'.format(study_area,output_type),False)

Map.view()
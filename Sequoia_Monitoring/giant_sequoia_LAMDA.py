"""
   Copyright 2023 Ian Housman

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

# Adaptation of LAMDA z-score approach to use Sentinel 2 data to monitor Giant Sequoia mortality
####################################################################################################
import os,sys,pandas,json
#Module imports
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.path.dirname(os.getcwd()),'Production'))
import LAMDA_Lib as ll
ee = ll.ee
Map = ll.Map
ee.Initialize()
Map.clearMap()
####################################################################################################
mortality_spreadsheet = r"Q:\LAMDA_workspace\giant-sequoia-monitoring\Inputs\mortality_record_keys.xlsx"
past_mortality = ee.FeatureCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/SEGI_MonarchMortality_202009')
monitoring_sites = ee.FeatureCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/Trees_of_Special_Interest')
####################################################################################################
# User parameters
indexNames=['NBR']
startJulians = range(190,250+1,8)
analysisLength = 8
# startJulian=int(ee.Date('2017-09-01').format('DDD').getInfo())
# endJulian = int(ee.Date('2017-09-30').format('DDD').getInfo())
analysisYears=[2020]
baselineLength = 3
baselineGap = 0
zReducer = ee.Reducer.percentile([70])
zThresh = -3
crs = 'EPSG:32611'#'EPSG:5070'
transform = [10,0,-2361915.0,0,-10,3177735.0]
scale = None
exportBucket = 'lamda-raw-outputs'
exportAreaName = ''
exportArea = None
exportRawZ = False



mortality_df = pandas.read_excel(mortality_spreadsheet)
mortality_json = json.loads(mortality_df.to_json(orient='table'))['data']
mortality_dict = {}
for row in mortality_json:mortality_dict[row['STI_Code']] = row

join_values_excel = list(mortality_dict.keys())
mortality_dict = ee.Dictionary(mortality_dict)

join_values_original = past_mortality.toList(10000,0).map(lambda f:ee.Feature(f).get('STI_ID')).getInfo()
missing_keys = [k for k in join_values_original if k not in join_values_excel]
print(missing_keys)
def joinMortality(f,join_fieldEE= 'STI_ID'):return ee.Feature(f.setMulti(ee.Dictionary(mortality_dict.get(f.get(join_fieldEE)))))
past_mortality = past_mortality.filter(ee.Filter.inList('STI_ID',missing_keys).Not())
past_mortality = ee.FeatureCollection(past_mortality.map(joinMortality))
# print(past_mortality.first().toDictionary().getInfo())
# ####################################################################################################
# print(monitoring_sites.first().toDictionary().getInfo())
# zScores = []
# composites = []
# for analysisYear in analysisYears:
#    startYear = analysisYear-baselineGap-baselineLength
#    endYear = analysisYear
#    for startJulian in startJulians:
#       endJulian = startJulian+analysisLength-1
#       print(startJulian,endJulian)
#       s2Images=ll.gv.getProcessedSentinel2Scenes(\
#       monitoring_sites,
#       startYear,
#       endYear,
#       startJulian,
#       endJulian,
#       applyQABand = False,
#       applyCloudScore = False,
#       applyShadowShift = False,
#       applyTDOM = True,
#       cloudScoreThresh = 20,
#       performCloudScoreOffset = True,
#       cloudScorePctl = 10,
#       cloudHeights = ee.List.sequence(500,10000,500),
#       zScoreThresh = -1,
#       shadowSumThresh = 0.35,
#       contractPixels = 1.5,
#       dilatePixels = 3.5,
#       shadowSumBands = ['nir','swir1'],
#       resampleMethod = 'bicubic',
#       toaOrSR = 'TOA',
#       convertToDailyMosaics = False,
#       applyCloudProbability = True,
#       preComputedCloudScoreOffset = None,
#       preComputedTDOMIRMean = None,
#       preComputedTDOMIRStdDev = None,
#       cloudProbThresh = 40)

#       z = ll.getZ(s2Images,indexNames,startJulian,endJulian,analysisYear,baselineLength,baselineGap,zReducer,zThresh,crs,transform,scale,exportBucket,exportAreaName,exportArea,exportRawZ).select([0])
#       imageDate = ee.Date.fromYMD(analysisYear,1,1).advance(startJulian,'day').advance(-1,'day').millis()
#       z = z.set('system:time_start',imageDate).reproject(crs,transform)
#       composite = s2Images.filter(ee.Filter.calendarRange(analysisYear,analysisYear,'year')).select(['red','nir','swir1','swir2','NDVI','NDMI','NBR']).median().set('system:time_start',imageDate).reproject(crs,transform)
#       zScores.append(z)
#       composites.append(composite.addBands(z.divide(10).float()))
# composites = ee.ImageCollection(composites)
# zScores = ee.ImageCollection(zScores)
# # print(zScores.size().getInfo())
# compositeVizParams = ll.gv.vizParamsFalse
# compositeVizParams['dateFormat']='YYMMdd'
# compositeVizParams['advanceInterval']='day'
# Map.addTimeLapse(composites,compositeVizParams,'Composites')
# Map.addTimeLapse(zScores,{'min':-3,'max':2,'palette':'F00,888,00F','dateFormat':'YYMMdd','advanceInterval':'day'},'Raw Z-scores')
monitoring_sites = monitoring_sites.map(lambda f:ee.Feature(f).buffer(10))
# print(monitoring_sites.first().getInfo())
Map.addLayer(monitoring_sites,{'layerType':'geeVectorImage','strokeColor':'0F0'},'Trees of Special Interest')
Map.addLayer(past_mortality.map(lambda f:ee.Feature(f).buffer(10)),{'layerType':'geeVectorImage','strokeColor':'F00'},'Mortality 2020-09')
####################################################################################################
# View map
Map.centerObject(past_mortality)
Map.setQueryCRS(crs)
Map.setQueryTransform(transform)
Map.turnOnInspector()
Map.view()

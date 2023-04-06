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

#TCC tile moving window visualization
####################################################################################################
import os,sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'Production'))
#Module imports
import LAMDA_Lib as ll
ee = ll.ee
Map = ll.Map
ee.Initialize()
Map.clearMap()
####################################################################################################
past_mortality = ee.FeatureCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/SEGI_MonarchMortality_202009')
monitoring_sites = ee.FeatureCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/Trees_of_Special_Interest')
####################################################################################################

indexNames=['NBR']
startJulians = range(190,250+1,10)
analysisLength = 15
# startJulian=int(ee.Date('2017-09-01').format('DDD').getInfo())
# endJulian = int(ee.Date('2017-09-30').format('DDD').getInfo())
analysisYear=2020
baselineLength = 3
baselineGap = 0
zReducer = ee.Reducer.percentile([70])
zThresh = -3
crs = 'EPSG:5070'
transform = [10,0,-2361915.0,0,-10,3177735.0]
scale = None
exportBucket = 'lamda-raw-outputs'
exportAreaName = ''
exportArea = None
exportRawZ = False


startYear = analysisYear-baselineGap-baselineLength
endYear = analysisYear

####################################################################################################
print(monitoring_sites.first().toDictionary().getInfo())
zScores = []
composites = []
for startJulian in startJulians:
   endJulian = startJulian+analysisLength-1
   print(startJulian,endJulian)
   s2Images=ll.gv.getProcessedSentinel2Scenes(\
   monitoring_sites,
   startYear,
   endYear,
   startJulian,
   endJulian,
   applyQABand = False,
   applyCloudScore = False,
   applyShadowShift = False,
   applyTDOM = True,
   cloudScoreThresh = 20,
   performCloudScoreOffset = True,
   cloudScorePctl = 10,
   cloudHeights = ee.List.sequence(500,10000,500),
   zScoreThresh = -1,
   shadowSumThresh = 0.35,
   contractPixels = 1.5,
   dilatePixels = 3.5,
   shadowSumBands = ['nir','swir1'],
   resampleMethod = 'bicubic',
   toaOrSR = 'TOA',
   convertToDailyMosaics = False,
   applyCloudProbability = True,
   preComputedCloudScoreOffset = None,
   preComputedTDOMIRMean = None,
   preComputedTDOMIRStdDev = None,
   cloudProbThresh = 40)

   z = ll.getZ(s2Images,indexNames,startJulian,endJulian,analysisYear,baselineLength,baselineGap,zReducer,zThresh,crs,transform,scale,exportBucket,exportAreaName,exportArea,exportRawZ)
   imageDate = ee.Date.fromYMD(analysisYear,1,1).advance(startJulian,'day').advance(-1,'day').millis()
   z = z.set('system:time_start',imageDate).reproject(crs,transform)
   composite = s2Images.median().set('system:time_start',imageDate).reproject(crs,transform)
   zScores.append(z)
   composites.append(composite)
composites = ee.ImageCollection(composites)
zScores = ee.ImageCollection(zScores)
# print(zScores.size().getInfo())
compositeVizParams = ll.gv.vizParamsFalse
compositeVizParams['dateFormat']='YYMMdd'
compositeVizParams['advanceInterval']='day'
Map.addTimeLapse(composites,compositeVizParams,'Composites')
Map.addTimeLapse(zScores.select([0]),{'min':-3,'max':2,'palette':'F00,888,00F','dateFormat':'YYMMdd','advanceInterval':'day'},'Raw Z-scores')

Map.addLayer(monitoring_sites.map(lambda f:f.geometry().buffer(30)),{'layerType':'geeVectorImage'},'Trees of Special Interest')
Map.addLayer(past_mortality.map(lambda f:f.geometry().buffer(30)),{'layerType':'geeVectorImage'},'Mortality 2020-09')
####################################################################################################
# View map
Map.setQueryCRS(crs)
Map.setQueryTransform(transform)
Map.turnOnInspector()
Map.view()

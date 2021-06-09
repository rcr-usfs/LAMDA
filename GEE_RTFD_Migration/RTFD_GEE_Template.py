"""
   Copyright 2021 Ian Housman

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
#Template script to run the Real Time Forest Disturbance (RTFD) Mapper in Google Earth Engine
#This method is a pixel-wise adaptation of the original RTFD algorithms
#Intended to work within the geeViz package with the RTFD_GEE_Lib script
####################################################################################################
####################################################################################################
from RTFD_GEE_Lib import *
####################################################################################################
#Specify user parameters

#Parameters used for both RTFD Z-Score and TDD methods
#Specify years to run RTFD Z-Score and TDD methods
analysisYears = [2020]

nDays = 32

startJulians = [201,216,231]#range(145,265+1,8)#range(65,321+1,8)#[320,335,350]

#Which indices to use
#Options are ['blue','green','red','nir','swir1','swir2','temp',NDVI','NBR','NDMI]
#The minimum of the z-score or slope is taken to reduce multiple bands/indices specified
indexNames = ['NBR']

###########################################
#TDD-only params
#Specify number of years (inclusive of the analysis year) 
#to run the trend change detection (TDD) method across
tddEpochLength = 5

#Change threshold for TDD (slope) 
#Generally around -0.03 to -0.08 works well
slopeThresh = -0.05

#How to summarize values for annual TDD composites
tddAnnualReducer = ee.Reducer.percentile([50])

###########################################
#Z-score-only params
#Specify the number of years to include in the baseline for the z-score method
zBaselineLength = 3

#Specify the number of years between the analyss year and baseline
#Useful if an area experienced change two years in a row
baselineGap = 1

#Change threshold for z (generally somewhere from -2 to -3 works well)
#Use higher number to include more loss
zThresh = -2.5

#How to summarize the daily z values for the analysis period
#User a lower percentile to include more loss
zReducer = ee.Reducer.percentile([50])

###########################################
#Parameters for MODIS image processing
resampleMethod = 'bicubic'
zenithThresh = 90
addLookAngleBands = True
#Cloud masking params
applyCloudScore = True
applyTDOM = True
cloudScoreThresh = 20
performCloudScoreOffset = False
cloudScorePctl = 10
zScoreThresh = -1
shadowSumThresh = 0.35
contractPixels = 0
dilatePixels = 2.5

#If available, bring in preComputed cloudScore offsets and TDOM stats
#Set to null if computing on-the-fly is wanted
#These have been pre-computed for all CONUS for MODIS - if running over AK or HI set to None
cloudScoreTDOMStatsDir = 'projects/gtac-rtfd/assets/MODIS-CS-TDOM-Stats'
cloudScoreTDOMStats = ee.ImageCollection('projects/USFS/FHAAST/RTFD/TDOM_Stats')\
            .map(lambda img: img.updateMask(img.neq(-32768)))\
            .mosaic()
            
preComputedCloudScoreOffset = None#cloudScoreTDOMStats.select(['cloudScore_p'+str(cloudScorePctl)])

#The TDOM stats are the mean and standard deviations of the two bands used in TDOM
#By default, TDOM uses the nir and swir1 bands
preComputedTDOMIRMean = None#cloudScoreTDOMStats.select(['.*_mean']).divide(10000)
preComputedTDOMIRStdDev = None#cloudScoreTDOMStats.select(['.*_stdDev']).divide(10000)

#Use this if outside CONUS
# preComputedCloudScoreOffset, preComputedTDOMIRMean, preComputedTDOMIRStdDev = None,None,None

###########################################
#Analysis area masking parameters
#Whether to apply LCMS tree mask
applyLCMSTreeMask = True

###########################################
#Exporting params
#Projection info
crs_dict = {'AK':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",55],PARAMETER["standard_parallel_2",65],PARAMETER["latitude_of_center",50],PARAMETER["longitude_of_center",-154],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1]]',
            'HI':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",3],PARAMETER["longitude_of_center",-157],PARAMETER["standard_parallel_1",8],PARAMETER["standard_parallel_2",18],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
            'CONUS':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",23],PARAMETER["longitude_of_center",-96],PARAMETER["standard_parallel_1",29.5],PARAMETER["standard_parallel_2",45.5],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'
            }
transform_dict = {'AK': [240,0,-51375,0,-240,1512585],
                  'HI': [240,0,-342585,0,-240,2127135],
                  'CONUS': [240,0,-2361915.0,0,-240,3177735.0]
                  }
export_area_dict = {'AK':ee.FeatureCollection("TIGER/2018/States").filter(ee.Filter.eq('NAME','Alaska')),
                    'HI':ee.FeatureCollection("TIGER/2018/States").filter(ee.Filter.eq('NAME','Hawaii')),
                    'CONUS': ee.FeatureCollection('projects/lcms-292214/assets/CONUS-Ancillary-Data/conus')}

#Export area name - provide a descriptive name for the study area
#Choose CONUS or AK
exportAreaName = 'AK'

crs = crs_dict[exportAreaName]
transform = transform_dict[exportAreaName]#Specify transform if scale is None and snapping to known grid is needed
scale = None #Specify scale if transform is None

#Google Cloud Storage bucket to export outputs to
exportBucket ='rtfd-scratch'

#Whether to export various outputs
#Whether to export each individual raw z score or TDD trend slope
exportRawZ = False
exportRawSlope = False

#Whether to export the final thresholded change count
exportZOutputs = False
exportTDDOutputs = False



#Area to export
# exportArea =ee.Geometry.Polygon(
#         [[[-84.28172252682539, 45.13859495600731],
#           [-84.28172252682539, 44.63654878793849],
#           [-83.62254283932539, 44.63654878793849],
#           [-83.62254283932539, 45.13859495600731]]], None, False)
exportArea = export_area_dict[exportAreaName]
#Whether to add prelim outputs to map to view
runGEEViz = True	

#######################################################
#Set up tree masks
#Set up union of all years needed
startYear = min(analysisYears) - max([tddEpochLength,zBaselineLength]) - baselineGap
endYear = max(analysisYears)

#Pull in lcms data for masking
lcms = ee.ImageCollection("USFS/GTAC/LCMS/v2020-5").filter(ee.Filter.calendarRange(startYear,endYear,'year'))
lcmsChange = lcms.select(['Change'])
lcmsChange = lcmsChange.map(lambda img: img.gte(2).And(img.lte(4))).max().selfMask()
lcmsTreeMask = lcms.select(['Land_Cover']).map(lambda img: img.lte(6)).max().selfMask()
# Map.addLayer(lcmsChange,{'min':1,'max':1,'palette':'800'},'LCMS Change',False)
# Map.addLayer(lcmsTreeMask,{'min':1,'max':1,'palette':'080','classLegendDict':{'Trees':'080'}},'LCMS Trees',False)

akTreeMask = ee.Image('projects/gtac-rtfd/assets/Ancillary/AK_forest_mask')
hiTreeMask = ee.Image("USGS/NLCD_RELEASES/2016_REL/2016_HI").gte(10).selfMask()
# Map.addLayer(akTreeMask,{'min':1,'max':1,'palette':'080','classLegendDict':{'Trees':'080'}},'AK FIA Trees',False)
# Map.addLayer(exportArea,{},'Study Area')
tree_mask_dict = {'CONUS':akTreeMask,
                  'AK':akTreeMask,
                  'HI':hiTreeMask}
tree_mask = tree_mask_dict[exportAreaName]
####################################################################################################
# rtfd_wrapper(analysisYears, startJulians, nDays , zBaselineLength, tddEpochLength, baselineGap , indexNames,zThresh,slopeThresh,zReducer, tddAnnualReducer,zenithThresh,addLookAngleBands,applyCloudScore, applyTDOM,cloudScoreThresh,performCloudScoreOffset,cloudScorePctl, zScoreThresh, shadowSumThresh, contractPixels,dilatePixels,resampleMethod,preComputedCloudScoreOffset,preComputedTDOMIRMean,preComputedTDOMIRStdDev, tree_mask,crs,transform, scale,exportBucket,exportAreaName,exportArea,exportRawZ,exportRawSlope,exportZOutputs,exportTDDOutputs)

computeCloudScoreTDOMStats(2015,2020,120,280,exportArea,cloudScoreTDOMStatsDir,exportAreaName,crs,transform)
if runGEEViz:
	Map.view()


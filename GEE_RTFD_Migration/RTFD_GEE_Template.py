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

nDays = 16

startJulians = [155,170,185,200]

#Which indices to use
#Options are ['blue','green','red','nir','swir1','swir2','temp',NDVI','NBR','NDMI]
#The minimum of the z-score or slope is taken to reduce multiple bands/indices specified
indexNames = ['NBR','NDVI']

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
#These have been pre-computed for all CONUS for MODIS
cloudScoreTDOMStats = ee.ImageCollection('projects/USFS/FHAAST/RTFD/TDOM_Stats')\
            .map(lambda img: img.updateMask(img.neq(-32768)))\
            .mosaic()
            
preComputedCloudScoreOffset = cloudScoreTDOMStats.select(['cloudScore_p'+str(cloudScorePctl)])

#The TDOM stats are the mean and standard deviations of the two bands used in TDOM
#By default, TDOM uses the nir and swir1 bands
preComputedTDOMIRMean = cloudScoreTDOMStats.select(['.*_mean']).divide(10000)
preComputedTDOMIRStdDev = cloudScoreTDOMStats.select(['.*_stdDev']).divide(10000)

#Use this if outside CONUS
# preComputedCloudScoreOffset, preComputedTDOMIRMean, preComputedTDOMIRStdDev = None,None,None

###########################################
#Analysis area masking parameters
#Whether to apply LCMS tree mask
applyLCMSTreeMask = True

###########################################
#Exporting params
#Projection info
crs = 'EPSG:5070'
transform = [240,0,-2361915.0,0,-240,3177735.0] #Specify transform if scale is None and snapping to known grid is needed
scale = None #Specify scale if transform is None

#Google Cloud Storage bucket to export outputs to
exportBucket ='rtfd-scratch'

#Whether to export various outputs
#Whether to export each individual raw z score or TDD trend slope
exportRawZ = False
exportRawSlope = False

#Whether to export the final thresholded change count
exportZOutputs = True
exportTDDOutputs = True

#Export area name - provide a descriptive name for the study area
exportAreaName = 'Mich_Defol_Test'

#Area to export
exportArea =ee.Geometry.Polygon(
        [[[-84.28172252682539, 45.13859495600731],
          [-84.28172252682539, 44.63654878793849],
          [-83.62254283932539, 44.63654878793849],
          [-83.62254283932539, 45.13859495600731]]], None, False)

#Whether to add prelim outputs to map to view
runGEEViz = True	

####################################################################################################
rtfd_wrapper(analysisYears, startJulians, nDays , zBaselineLength, tddEpochLength, baselineGap , indexNames,zThresh,slopeThresh,zReducer, tddAnnualReducer,zenithThresh,addLookAngleBands,applyCloudScore, applyTDOM,cloudScoreThresh,performCloudScoreOffset,cloudScorePctl, zScoreThresh, shadowSumThresh, contractPixels,dilatePixels,resampleMethod,preComputedCloudScoreOffset,preComputedTDOMIRMean,preComputedTDOMIRStdDev, applyLCMSTreeMask,crs,transform, scale,exportBucket,exportAreaName,exportArea,exportRawZ,exportRawSlope,exportZOutputs,exportTDDOutputs)

if runGEEViz:
	Map.view()

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
analysisYears = [2021]

initialStartJulian = 145
frequency = 8
# nDays = 16#32 #16 for CONUS, something like 64 or so for HI, 32 or so for AK
nDaysDict = {
  'CONUS':16,
  'AK':32,
  'AK_main':32,
  'AK_SE':32
}
startJulians = [145]#range(145,185,8)#range(65,321+1,8)#[201,216,231]#range(145,265+1,8)#range(65,321+1,8)#[320,335,350]

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
baselineGap = 0

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
addLookAngleBands = False
#Cloud masking params
applyCloudScore = True
applyTDOM = True
cloudScoreThresh = 20   
performCloudScoreOffset = False #Only need to set to True if running RTFD over bright areas (not the case if only running over dense trees. Can help avoid cloud masking commission over PJ forests)
cloudScorePctl = 10
zScoreThresh = -1
shadowSumThresh = 0.35
contractPixels = 0
dilatePixels = 2.5

#How many periods to include in persistence
persistence_n_periods =3

#If available, bring in preComputed cloudScore offsets and TDOM stats
#Set to null if computing on-the-fly is wanted
#These have been pre-computed for all CONUS, AK, and HI for MODIS. If outside these areas, set to None below
cloudScoreTDOMStatsDir = 'projects/gtac-rtfd/assets/MODIS-CS-TDOM-Stats'
# conuscloudScoreTDOMStats = ee.ImageCollection('projects/USFS/FHAAST/RTFD/TDOM_Stats')\
#             .map(lambda img: img.updateMask(img.neq(-32768)))\
           
cloudScoreTDOMStats = ee.ImageCollection(cloudScoreTDOMStatsDir).mosaic()
# cloudScoreTDOMStats = conuscloudScoreTDOMStats.merge(akHICloudScoreTDOMStats).mosaic()

preComputedCloudScoreOffset = cloudScoreTDOMStats.select(['cloudScore_p{}'.format(cloudScorePctl)])

#The TDOM stats are the mean and standard deviations of the two bands used in TDOM
#By default, TDOM uses the nir and swir1 bands
preComputedTDOMIRMean = cloudScoreTDOMStats.select(['.*_mean']).divide(10000)
preComputedTDOMIRStdDev =cloudScoreTDOMStats.select(['.*_stdDev']).divide(10000)
# Map.addLayer(cloudScoreTDOMStats,{},'cloudScoreTDOMStats')
#Use this if outside CONUS, AK, and HI
# preComputedCloudScoreOffset, preComputedTDOMIRMean, preComputedTDOMIRStdDev = None,None,None

###########################################
#Exporting params
#Projection info
crs_dict = {'AK':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",55],PARAMETER["standard_parallel_2",65],PARAMETER["latitude_of_center",50],PARAMETER["longitude_of_center",-154],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1]]',
              'AK_main':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",55],PARAMETER["standard_parallel_2",65],PARAMETER["latitude_of_center",50],PARAMETER["longitude_of_center",-154],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1]]',
            'AK_SE':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",55],PARAMETER["standard_parallel_2",65],PARAMETER["latitude_of_center",50],PARAMETER["longitude_of_center",-154],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1]]',
            'HI':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",3],PARAMETER["longitude_of_center",-157],PARAMETER["standard_parallel_1",8],PARAMETER["standard_parallel_2",18],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
            'CONUS':
              'PROJCS["Albers_Conical_Equal_Area",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["latitude_of_center",23],PARAMETER["longitude_of_center",-96],PARAMETER["standard_parallel_1",29.5],PARAMETER["standard_parallel_2",45.5],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
              'MX':'EPSG:32613'
            }
transform_dict = {'AK': [240,0,-51375,0,-240,1512585],
                  'AK_main': [240,0,-51375,0,-240,1512585],
                  'AK_SE': [240,0,-51375,0,-240,1512585],
                  'HI': [240,0,-342585,0,-240,2127135],
                  'CONUS': [240,0,-2361915.0,0,-240,3177735.0],
                  'MX':[240,0,-2361915.0,0,-240,3177735.0]
                  }

export_area_dict = {'AK':ee.FeatureCollection('projects/gtac-rtfd/assets/Ancillary/AK_main').merge(ee.FeatureCollection('projects/gtac-rtfd/assets/Ancillary/AK_se')),
                    'AK_main': ee.FeatureCollection('projects/gtac-rtfd/assets/Ancillary/AK_main'),
                    'AK_SE': ee.FeatureCollection('projects/gtac-rtfd/assets/Ancillary/AK_se'),
                    'HI':ee.FeatureCollection("TIGER/2018/States").filter(ee.Filter.eq('NAME','Hawaii')),
                    'CONUS': ee.FeatureCollection('projects/lcms-292214/assets/CONUS-Ancillary-Data/conus'),
                    'MX':ee.FeatureCollection("FAO/GAUL/2015/level0").filter(ee.Filter.eq('ADM0_NAME','Mexico'))}


#Export area name - provide a descriptive name for the study area
#Choose CONUS or AK
exportAreaName = 'AK'

crs = crs_dict[exportAreaName]
transform = transform_dict[exportAreaName]#Specify transform if scale is None and snapping to known grid is needed
scale = None #Specify scale if transform is None

#Google Cloud Storage bucket to export outputs to
exportBucket ='rtfd-2021'

#Bucket final outputs will be uploaded to
deliverable_output_bucket = 'rtfd-delivery'

#Location to copy outputs to locally
local_output_dir =r'Q:\RTFD_gee_method\Outputs_2021'# r'Q:\RTFD_gee_method\data7'

#Location of gsutil 
#May need a full path to the location if it's not in the PATH
gsutil_path = 'gsutil.cmd'

#Regex to filter outputs
output_filter_strings = ['*CONUS_RTFD*','*AK_RTFD*']#'*CONUS_RTFD_Z*ay2020*','*CONUS_RTFD_TDD*yrs2016-2020*']

#Whether to export various outputs
#Whether to export each individual raw z score or TDD trend slope
exportRawZ = True
exportRawSlope = True



#Post processing params

#Set up some possible color palette
continuous_palette_chastain = ['a83800','ff5500','e0e0e0','a4ff73','38a800']
continuous_palette_lcms =['d54309','3d4551','00a398']  
continuous_palette = continuous_palette_chastain

#Provide a key to find for each type of RTFD data (_TDD_ and _Z_ work fine for raw outputs)
#Main things to change are the stretch and stretch_mult to try out. 
#The stretch is used to clip the complete raw data in a min max fashion, then the stretch_mult multiplies that number
#For example, z scores typically go from around -10 to 10 at the tails
#If a stretch of 10 is provided, the data are first clipped to -10 to 10 stdDev, and then 10 is added
#Now all values range from 0-20. Then the stretch_mult is applied so all values range from 0-200 and nicely fit in 8 bit space (0-255)
#Changing the stretch to a smaller number will cut off more of the tails of the distribution, but highlight more subtle change
#If changing the stretch to a larger number, the stretch_mult will need lowered so it still fits into 8 bit space
#This is currently done manually since a simple 0-255 stretch is currently not utilized
post_process_dict = {
  '_TDD_':{'palette':continuous_palette,
      'scale_factor':10000,
      'thresh':slopeThresh,
      'stretch' : slopeThresh*-2},
  '_Z_':{'palette':continuous_palette,
      'scale_factor':1000,
      'thresh':zThresh,
      'stretch' : int(zThresh*-2)},
}


#Area to export
exportArea = export_area_dict[exportAreaName]

nDays = nDaysDict[exportAreaName]

#Whether to add prelim outputs to map to view
runGEEViz = False	

#Whether to track tasks
trackTasks = False
#######################################################
#Set up tree masks
#Set up union of all years needed
startYear = min(analysisYears) - max([tddEpochLength,zBaselineLength]) - baselineGap
endYear = max(analysisYears)

#Pull in lcms data for masking
lcms = ee.ImageCollection("USFS/GTAC/LCMS/v2020-5").filter(ee.Filter.calendarRange(startYear,endYear,'year'))
# lcmsChange = lcms.select(['Change'])
# lcmsChange = lcmsChange.map(lambda img: img.gte(2).And(img.lte(4))).max().selfMask()
lcmsTreeMask = lcms.select(['Land_Cover']).map(lambda img: img.lte(6)).max()
# Map.addLayer(lcmsChange,{'min':1,'max':1,'palette':'800'},'LCMS Change',False)
# Map.addLayer(lcmsTreeMask,{'min':1,'max':1,'palette':'080','classLegendDict':{'Trees':'080'}},'LCMS Trees',False)

#Pull in AK and HI tree masks (no LCMS currently available across all of AK or any of HI)
akTreeMask = ee.Image('projects/gtac-rtfd/assets/Ancillary/AK_forest_mask')
hiTreeMask = ee.Image("USGS/NLCD_RELEASES/2016_REL/2016_HI").gte(10)

global_tcc = ee.ImageCollection("NASA/MEASURES/GFCC/TC/v3")
global_tcc= global_tcc.filter(ee.Filter.eq('year',2015)).mosaic().select([0]);

hansen = ee.Image("UMD/hansen/global_forest_change_2020_v1_8").select([0]).gte(5);
# Map.addLayer(global_tcc,{'min':10,'max':80,'palette':'000,0F0'},'global_tcc')
global_tree = global_tcc.gte(10).selfMask()

# Map.addLayer(global_tree,{},'global tree')
# Map.addLayer(akTreeMask,{},'AK tree')
#Mosaic all tree masks
#Set to None if applying a tree mask isn't needed
tree_mask = ee.Image.cat([lcmsTreeMask,akTreeMask,hiTreeMask,global_tree,hansen]).reduce(ee.Reducer.max()).selfMask()
# Map.addLayer(tree_mask,{},'all tree mask')
# exportToDriveWrapper(tree_mask,'tree-export-test','test',roi= exportArea,scale= None,crs = crs,transform = transform,outputNoData = 255)
####################################################################################################
#Function calls and scratch space
#Comment out each section as needed

#Compute cloudScore and TDOM stats if they are not available
# cs_dates= {'MX':[121,304]}
#               # 'AK_main':[152,243],
#               # 'AK_SE':[152,243]}
# #             'CONUS':[152,273],
# #             'HI':[1,365]}
# for exportAreaName in cs_dates.keys():
#   computeCloudScoreTDOMStats(2018,2021,cs_dates[exportAreaName][0],cs_dates[exportAreaName][1],export_area_dict[exportAreaName],cloudScoreTDOMStatsDir,exportAreaName,crs_dict[exportAreaName],transform_dict[exportAreaName])


#Run RTFD using parameters above
#It will overwrite outputs if they already exist in cloudStorage

# tracking_filenames = rtfd_wrapper(analysisYears, startJulians, nDays , zBaselineLength, tddEpochLength, baselineGap , indexNames,zThresh,slopeThresh,zReducer, tddAnnualReducer,zenithThresh,addLookAngleBands,applyCloudScore, applyTDOM,cloudScoreThresh,performCloudScoreOffset,cloudScorePctl, zScoreThresh, shadowSumThresh, contractPixels,dilatePixels,resampleMethod,preComputedCloudScoreOffset,preComputedTDOMIRMean,preComputedTDOMIRStdDev, tree_mask,crs,transform, scale,exportBucket,exportAreaName,exportArea,exportRawZ,exportRawSlope)

# tml.trackTasks2(id_list = tracking_filenames)
# tracking_filenames_tifs = [i+'.tif' for i in tracking_filenames]
# print(tracking_filenames_tifs)
# sync_rtfd_outputs(exportBucket,local_output_dir,tracking_filenames_tifs)
if __name__ == '__main__':

  for exportAreaName in ['CONUS','AK']:#,'AK']:
    crs = crs_dict[exportAreaName]
    transform = transform_dict[exportAreaName]
    nDays = nDaysDict[exportAreaName]
    exportArea = export_area_dict[exportAreaName]
    p = Process(target=operational_rtfd, args=(initialStartJulian,frequency,nDays, zBaselineLength, tddEpochLength, baselineGap , indexNames,zThresh,slopeThresh,zReducer, tddAnnualReducer,zenithThresh,addLookAngleBands,applyCloudScore, applyTDOM,cloudScoreThresh,performCloudScoreOffset,cloudScorePctl, zScoreThresh, shadowSumThresh, contractPixels,dilatePixels,resampleMethod,preComputedCloudScoreOffset,preComputedTDOMIRMean,preComputedTDOMIRStdDev, tree_mask,crs,transform, scale,exportBucket,exportAreaName,exportArea,exportRawZ,exportRawSlope,local_output_dir,gsutil_path,crs_dict,post_process_dict,persistence_n_periods,deliverable_output_bucket,))
    p.start()
  limitProcesses(1)


# calc_persistence_wrapper(local_output_dir,exportAreaName,indexNames,time.localtime()[0], post_process_dict)
#After exports are done, pull them down locally 
#If you get an error when running this, you may need to re-authenticate
#To do this, run gcloud auth login
#Make sure you open the url in a browswer that is pointing to the Google account that has access to the bucket you're pulling from
# sync_rtfd_outputs(exportBucket,local_output_dir,output_filter_strings,gsutil_path)

#The correct the CRS, set no data, update the stats, convert to 8 bit, and set a colormap
# post_process_rtfd_local_outputs(local_output_dir,crs_dict,post_process_dict)

#View map
# if runGEEViz:
	# Map.view()

#Track tasks
# if trackTasks:
  # tml.trackTasks2()

# tml.failedTasks()
# tml.batchCancel()
# tml.trackTasks2()
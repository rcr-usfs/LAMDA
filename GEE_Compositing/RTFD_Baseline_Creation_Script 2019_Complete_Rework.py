

# #RTFD Baseline Creation Script 2019 01-05-16-w/Reproject

# #Code written by: Ian Housman
# #Original code written by: Robert Chastain

# #Module imports
import exportManager
from multiprocessing import Pool,Process
import multiprocessing,sys,time,os,urllib,threading,subprocess,time,datetime

# sys.path.append('//166.2.126.25/glrc_vct/Housman_Code/')
from r_numpy_lib import *


# libPath = 'C:/USFS/gee-py-modules'
# libPath = 'G:/GEE/gee-py-modules'
# libPath = 'W:/gee-py-modules'
# libPath = 'C:/scratch/gee-modules'
# sys.path.append(libPath)
# os.chdir(libPath)
from geeViz.getImagesLib import *


#########################################################################
cloudScoreTDOMStats = ee.ImageCollection('projects/USFS/FHAAST/RTFD/TDOM_Stats')\
            .map(lambda img: img.updateMask(img.neq(-32768)))\
            .mosaic()
irMean = cloudScoreTDOMStats.select(['.*_mean']).divide(10000)
irStdDev = cloudScoreTDOMStats.select(['.*_stdDev']).divide(10000)

ellenwoodMask = ee.ImageCollection('projects/USFS/FHAAST/RTFD/Ellenwood_Forest_Mask').mosaic()



#########################################################################
#Define user parameters:

#Specify study area: Study area
#Can specify a country, provide a fusion table  or asset table (must add 
#.geometry() after it), or draw a polygon and make studyArea = drawnPolygon

mzs = ee.List.sequence(1,14).getInfo()#MZs to export

mzsF = ee.FeatureCollection('projects/USFS/LCMS-NFS/CONUS-Ancillary-Data/USGS_Multizones')

studyArea = mzsF

#Update the start julian
#The endJulian will be computed based on the compositingPeriod,
#compositingFrequency, and compositingPeriods
#compositingPeriod is the number of days to include in each composite
#compositingFrequency is how often composites will be created
#compositingPeriods is the number of periods (composites) that will be created
startJulian = 49
compositingPeriod = 16
compositingFrequency = 8
compositingPeriods = 3


#Specify start and end years for all analyses
#More than a 3 year span should be provided for time series methods to work 
#well. 
#Years to include data for TDOM
startYear = 2016
endYear = 2019


timeBuffer = 0

#Set up Names for the export
exportName = 'PY_TDD_Baseline_Medoid_cloudScore_TDOM_3min_240_Cubic_'

#Provide Drive folderlocation composites will be exported to
exportDriveFolder = 'RTFD-Baseline-Exports'

gs_bucket = 'rtfd-exports'
# exportLocalFolder = 'Q:/Scripts/'+ gs_bucket
exportLocalFolder = 'T:/baseline/TDD_baseline_data/'
exportLocalFolder2 = 'C:/TDD_baseline_data/'
if os.path.exists(exportLocalFolder) == False: 
    check_dir(exportLocalFolder2)
    exportLocalFolder = exportLocalFolder2

exportLocalFolder += gs_bucket

# syncCommand = 'Q:/Scripts/google-cloud-sdk/bin/gsutil.cmd -m cp -n -r gs://'+gs_bucket+' '+os.path.dirname(exportLocalFolder)
#syncCommand = 'W:/Installation_Programs/google-cloud-sdk/bin/gsutil.cmd -m cp -n -r gs://'+gs_bucket+' '+os.path.dirname(exportLocalFolder)
syncCommand = 'C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gsutil.cmd -m cp -n -r gs://'+gs_bucket+' '+os.path.dirname(exportLocalFolder)
#syncCommand = 'C:/Users/rchastain/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gsutil.cmd -m cp -n -r gs://'+gs_bucket+' '+os.path.dirname(exportLocalFolder)

#MODIS Params- params if sensorProgram is modis
#Whether to use daily MODIS (true) or 8 day composites (false)
#Daily images provide complete control of cloud/cloud shadow masking as well as compositing
#Daily images have a shorter lag time as well (~2-4 days) vs pre-computed
#8-day composites (~7 days)
daily = True

#If using daily, the following parameters apply
zenithThresh  = 45#If daily == True, Zenith threshold for daily acquisitions for including observations

despikeMODIS = False#Whether to despike MODIS collection
modisSpikeThresh = 0.1#Threshold for identifying spikes.  Any pair of images that increases and decreases (positive spike) or decreases and increases (negative spike) in a three image series by more than this number will be masked out



# Choose cloud/cloud shadow masking method
# Choices are a series of booleans for cloudScore, TDOM, and QA (if using daily images)
#CloudScore runs pretty quickly, but does look at the time series to find areas that 
#always have a high cloudScore to reduce comission errors- this takes some time
#and needs a longer time series (>5 years or so)
#TDOM also looks at the time series and will need a longer time series
applyCloudScore = True
applyQACloudMask = False#Whether to use QA bits for cloud masking


applyTDOM = True


#Cloud and cloud shadow masking parameters.
#If cloudScoreTDOM is chosen
#cloudScoreThresh: If using the cloudScoreTDOMShift method-Threshold for cloud 
#   masking (lower number masks more clouds.  Between 10 and 30 generally 
#   works best)
cloudScoreThresh = 20

#Whether to find if an area typically has a high cloudScore
#If an area is always cloudy, this will result in cloud masking omission
#For bright areas that may always have a high cloudScore
#but not actually be cloudy, this will result in a reduction of commission errors
#This procedure needs at least 5 years of data to work well
performCloudScoreOffset = True

#If performCloudScoreOffset = True:
#Percentile of cloud score to pull from time series to represent a minimum for 
#the cloud score over time for a given pixel. Reduces comission errors over 
#cool bright surfaces. Generally between 5 and 10 works well. 0 generally is a
#bit noisy but may be necessary in persistently cloudy areas
#Must choose 5 or 10 for precomputed cloudScore offset
cloudScorePctl = 10

#zScoreThresh: Threshold for cloud shadow masking- lower number masks out 
#less. Between -0.8 and -1.2 generally works well
zScoreThresh = -1

#shadowSumThresh: Sum of IR bands to include as shadows within TDOM and the 
#   shadow shift method (lower number masks out less)
shadowSumThresh = 0.35

#contractPixels: The radius of the number of pixels to contract (negative 
#   buffer) clouds and cloud shadows by. Intended to eliminate smaller cloud 
#   patches that are likely errors
#(1.5 results in a -1 pixel buffer)(0.5 results in a -0 pixel buffer)
#(1.5 or 2.5 generally is sufficient)
contractPixels = 0.5

#dilatePixels: The radius of the number of pixels to dilate (buffer) clouds 
#   and cloud shadows by. Intended to include edges of clouds/cloud shadows 
#   that are often missed
#(1.5 results in a 1 pixel buffer)(0.5 results in a 0 pixel buffer)
#(2.5 or 3.5 generally is sufficient)
dilatePixels = 1.5

#Minimum number of observations needed to be considered for medoid
minObs = 3

#Whether to include sensor and solar angles
includeSensorSolarAngles = True

#Manually specify which bands to export and what to multiply them by to get them into 16 bit range
exportBands = ['red','nir','blue','green','swir2','SensorZenith','SensorAzimuth','SolarAzimuth','SolarZenith','yearJulian']
multExportBands = [10000,10000,10000,10000,10000,1,1,1,1,1]

#Specify what bands to include in the medoid
medoidBands = ['red','nir','blue','green','swir2']


nThreads = 24
#Parameters to look at data with
vizParams = {'min':0.1,'max':[0.2,0.95,0.2],'bands':'swir2,nir,red'}

noDataValue = -32768

#Choose resampling method
#Can be one of 'near', 'bilinear', or 'bicubic'
resampleMethod = 'bicubic'

#Export params
crs = 'EPSG:5070';
gdal_crs = 'PROJCS["NAD_1983_Albers",GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9108"]],AUTHORITY["EPSG","4269"]],PROJECTION["Albers_Conic_Equal_Area"],PARAMETER["standard_parallel_1",29.5],PARAMETER["standard_parallel_2",45.5],PARAMETER["latitude_of_center",23],PARAMETER["longitude_of_center",-96],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["meters",1]]'
transform = [240,0,-2370945.0,0,-240,3189315.0];#Specify transform if scale is null and snapping to known grid is needed
scale = None#Specify scale if transform is null
#########################################################################
#########################################################################End user parameters
#########################################################################
#########################################################################
#########################################################################

#Start function calls
# Prepare dates
#Figure out the julians based on info above
startJulians = ee.List.sequence(startJulian,(startJulian +compositingPeriods*compositingFrequency)-1,compositingFrequency)
endJulians = startJulians.map(lambda i: ee.Number(i).add(compositingPeriod).subtract(1))
julianSets = startJulians.zip(endJulians).getInfo()
# print('Julian sets are:',julianSets);

endJulian = endJulians.get(endJulians.length().subtract(1)).getInfo()

#Wrap the dates if needed
if startJulian > endJulian:endJulian = endJulian + 365


startDate = ee.Date.fromYMD(startYear,1,1).advance(startJulian-1,'day')
endDate = ee.Date.fromYMD(endYear,1,1).advance(endJulian-1,'day')
# print('Start and end dates:', startDate.getInfo(), endDate.getInfo());

if applyCloudScore:useTempInCloudMask = True
else: useTempInCloudMask = False#Whether to use the temperature band in cloud masking- necessary to use temp in bright arid areas
#b1 = red
#b2 = nir
#b3 = blue
#b4 = green
#b5 = swirNotInLandsat
#b6 = swir1
#b7 = swir2
yearJulians = []
for year in ee.List.sequence(startYear+timeBuffer,endYear-timeBuffer).getInfo():
        year = int(year)
        startYearT = year-timeBuffer
        endYearT = year+timeBuffer
  
        #Iterate across each set of julian dates
        for js in julianSets:
                startJulianT,endJulianT= [int(js[0]),int(js[1])]
                yearJulians.append([startYearT,endYearT,startJulianT,endJulianT])

yearJulianSets  = exportManager.new_set_maker(yearJulians,exportManager.nCredentials)


#########################################################################
def exportYearJulianRange(startYearT,endYearT,startJulianT,endJulianT,credentialName):
        modisImages = getModisData(startYearT,endYearT,startJulianT,endJulianT,daily,applyQACloudMask,zenithThresh,useTempInCloudMask,includeSensorSolarAngles,resampleMethod)
        
        # Map.addLayer(modisImages.median(),vizParams,'nomasking',False)


        if applyCloudScore:
                print('Applying cloudScore')

                #Add cloudScore
                modisImages = modisImages.map(lambda img:img.addBands(modisCloudScore(img).rename(['cloudScore'])))

                if performCloudScoreOffset:
                        print('Computing cloudScore offset')
                #Find low cloud score pctl for each pixel to avoid comission errors (precomputed)
                        minCloudScore = cloudScoreTDOMStats.select(['cloudScore_p'+str(cloudScorePctl)])

                else:
                        print('Not computing cloudScore offset')
                        minCloudScore = ee.Image(0).rename(['cloudScore'])

                # Map.addLayer(minCloudScore,{'min':0,'max':20},'minCloudScore')
                #Apply cloudScore
                def applyCM(img):
                        cloudMask = img.select(['cloudScore']).subtract(minCloudScore).lt(cloudScoreThresh).focal_max(contractPixels).focal_min(dilatePixels).rename(['cloudMask'])
                        
                        return img.updateMask(cloudMask)
                
                modisImages = modisImages.map(applyCM)
                 
        # Map.addLayer(modisImages.median(),vizParams,'cloudMasking',False)


        if applyTDOM:
                print('Applying TDOM')
                #Find and mask out dark outliers
                modisImages = simpleTDOM2(modisImages,zScoreThresh,shadowSumThresh,contractPixels,dilatePixels,['nir','swir2'],irMean,irStdDev)

        # Map.addLayer(modisImages.median(),vizParams,'cloudMaskingShadowMasking',False)

        if despikeMODIS:
                print('Despiking MODIS')
                modisImages = despikeCollection(modisImages,modisSpikeThresh,'nir')
          


        #Add data data
        # f = ee.Image(modisImages.first())
        # f = addYearJulianDayBand(f)
        # print(f.bandNames().getInfo())
        modisImages = modisImages.map(addYearJulianDayBand);

        modisImages = modisImages.select(exportBands)
        

        modisImages = modisImages.map(lambda i: i.updateMask(i.select(medoidBands).mask().reduce(ee.Reducer.min())))
        
        #Compute the medoid composite
        mCount = modisImages.count().select([0])

        medoidBaseline  = medoidMosaicMSD(modisImages,medoidBands).updateMask(mCount.gte(minObs))
        
        medoidBaseline = medoidBaseline.updateMask(medoidBaseline.mask().reduce(ee.Reducer.min()))

        # Map.addLayer(medoidBaseline,vizParams,str(startYearT) + '_' + str(endYearT) + '_'+ str(startJulianT)+'_'+str(endJulianT))
        id_list = []
        #Iterate across each MZ
        for mz in mzs:
                print('Exporting mz:',int(mz))
                mz = int(mz)
                #Set up the output name for the export
                outputName =  exportName+'MZ'+format(mz, '02') + '_' +str(startYearT) + '_' + str(endYearT) + '_'+ format(startJulianT, '03')+'_'+format(endJulianT, '03')
                # fullOutputName = exportLocalFolder + outputName + '.zip'
                #Filter out the MZ outine
                mzT = mzsF.filter(ee.Filter.eq('FTP_Zone',mz)).geometry()

                #Clip medoid composite to MZ outlien
                imageT = medoidBaseline.clip(mzT)
                # imageT = ee.Image(1).clip(mzT)

                #Select bands for export, set the null value to a specified value, and export to Drive
                imageT = imageT.select(exportBands).multiply(multExportBands).int16()
                imageT = setNoData(imageT,noDataValue)
                
               
                t = ee.batch.Export.image.toCloudStorage(imageT, outputName, gs_bucket, outputName, None, mzT.bounds().getInfo()['coordinates'][0], None, crs, str(transform), 1e13)
              

                # t = ee.batch.Export.image.toDrive(imageT, outputName, exportDriveFolder, None, None, mzT.bounds().getInfo()['coordinates'][0], None, crs, transform, 1e13)
                
                id_list.append(outputName)
                t.start()
                # print(t)
        # Map.view()
        return id_list
        # trackTasks(id_list)
def limitProcesses(processLimit):
        while len(multiprocessing.process.active_children()) > processLimit:
                print (len(multiprocessing.process.active_children()),':active processes')
                time.sleep(5)
def trackTasks(credential_name,id_list,task_count = 1):
        while task_count > 0:
                tasks = ee.data.getTaskList()
                tasks = [i for i in tasks if i['description'] in id_list]
                ready = [i for i in tasks if i['state'] == 'READY']
                running = [i for i in tasks if i['state'] == 'RUNNING']
                completed = [i for i in tasks if i['state'] == 'COMPLETED']
                running_names = [[str(i['description']),str(datetime.timedelta(seconds = int(((time.time()*1000)-int(i['start_timestamp_ms']))/1000)))] for i in running]
                now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print(credential_name)
                print(len(ready),'tasks ready',now)
                print(len(running),'tasks running',now)
                print(len(completed),'tasks completed',now)
                print('Running names:')
                for rn in running_names:print(rn)
                print
                print
                time.sleep(5)
                task_count = len(ready) +len(running)
                
def exportYearJulianSet(i):
        id_list = []
        yearJulianSet = yearJulianSets[i]
        credentials = exportManager.GetPersistentCredentials(exportManager.credentials[i])
        credentialsName = os.path.basename(exportManager.credentials[i])
        exportManager.ee.Initialize(credentials)
        for startYearT,endYearT,startJulianT,endJulianT in yearJulianSet:
                ids =exportYearJulianRange(startYearT,endYearT,startJulianT,endJulianT,credentialsName)
                id_list.extend(ids)
        trackTasks(credentialsName,id_list)

def batchExport():
        for i in range(exportManager.nCredentials):
                
                p = Process(target = exportYearJulianSet,args = (i,),name = str(i))
                p.start()
                time.sleep(0.2)

        while len(multiprocessing.process.active_children()) > 0:
                print (len(multiprocessing.process.active_children())),':active export processes'
                syncer()
                time.sleep(1)
def syncer():
        print(syncCommand)
        call = subprocess.Popen(syncCommand)
        while call.poll() == None:
                print ('Still syncing:'),now()
                fixExports()
                time.sleep(5)

        fixExports()

def batchFixExports(tifSet):
        for tif in tifSet:
                print('Updating projection for:',base(tif))
                set_projection(tif,gdal_crs)
                set_no_data(tif, no_data_value = noDataValue, update_stats = True)
def fixExports():
        check_dir(exportLocalFolder)
        fix_report = check_end(exportLocalFolder) + 'fixed_rasters.csv'
        if os.path.exists(fix_report):
                oo = open(fix_report,'r')
                fix_lines = oo.readlines()
                oo.close()
        else:
                fix_lines = []

        tifs = glob(exportLocalFolder,'.tif')
        tifs_to_update = []
        for tif in tifs:

                if tif + '\n' not in fix_lines:
                        tifs_to_update.append(tif)
                        fix_lines.append(tif+'\n')
        

        if len(tifs_to_update)>0:
        
                tifSets = new_set_maker(tifs_to_update,nThreads)
                for tifSet in tifSets:
                        if len(tifSet) > 0:
                                p = Process(target = batchFixExports,args = (tifSet,))
                                p.start()
                                time.sleep(0.2)
                # limitProcesses(0)
        else:
                print('No rasters need fixed')

        oo = open(fix_report,'w')
        oo.writelines(fix_lines)
        oo.close()


        
        
if __name__ == '__main__':  

        # batchExport()
        
        #fixExports()
        # limitProcesses(0)
        syncer()
        
 #      limitProcesses(0)


        # limitProcesses(0)
        
# Map.launchGEEVisualization()

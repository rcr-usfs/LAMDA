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

# Script to run the LAndscape Monitoring and Detection Application (LAMDA) in Google Earth Engine
# This method is a pixel-wise adaptation of the original RTFD (Real Time Forest Disturbance) algorithms
# Intended to work within the geeViz package
####################################################################################################
import json, time, glob, ee, os, subprocess, multiprocessing
from google.cloud import storage
from multiprocessing import Process


ee.Authenticate()
ee.Initialize(project="gtac-lamda")
# Initialize GEE - using service account if possible
# try:
#     key_file = r"Q:\LAMDA_workspace\credentials\gtac-lamda-1bfc7752157b.json"
#     ee.Initialize(ee.ServiceAccountCredentials(json.load(open(key_file)), key_file))
#     print(ee.data._cloud_api_user_project)
#     print("Successfully initialized using service account GEE credentials")
# except Exception as e:
#     print(e)
#     print("Will use local GEE credentials")


import geeViz.changeDetectionLib as gv
import geeViz.taskManagerLib as tml
import LAMDA_register_cogs as rc


# import geeViz.cloudStorageManagerLib as csl

ee = gv.ee
Map = gv.Map
Map.clearMap()
import raster_processing_lib as rpl

# Set environment variable for GCS use
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file
tracking_filenames = []


####################################################################################################
def rename_blobs(bucket_name, old_name, new_name):
    """Renames a group of blobs."""
    # storage client instance
    storage_client = storage.Client()

    # get bucket by name
    bucket = storage_client.get_bucket(bucket_name)

    # list files stored in bucket
    all_blobs = bucket.list_blobs()

    # Renaming all files to lowercase:
    for blob in all_blobs:
        on = str(blob.name)
        nn = on.replace(old_name, new_name)
        new_blob = bucket.rename_blob(blob, new_name=nn)
        print("Blob {} has been renamed to {}".format(on, nn))


# rename_blobs("lamda-raw-outputs",'_RTFD_','_LAMDA_')
# Checks to see if a cloud storage object exists
def gcs_exists(bucket, filename):
    storage_client = storage.Client()
    stats = storage.Blob(bucket=storage_client.bucket(bucket), name=filename).exists(storage_client)
    return stats


# Function to compute cloudScore offsets and TDOM stats for MODIS
# Example call to compute cloudScore and TDOM stats if they are not available
# computeCloudScoreTDOMStats(2020,2020,152,212,exportArea,cloudScoreTDOMStatsDir,exportAreaName,crs,transform)
def computeCloudScoreTDOMStats(
    startYear, endYear, startJulian, endJulian, exportArea, exportPath, name, crs, transform, percentiles=[5, 10], cloudScoreThresh=20, cloudScorePctl=10, contractPixels=0, dilatePixels=2.5, performCloudScoreOffset=True, tdomBands=["nir", "swir2"]
):
    args = gv.formatArgs(locals())
    if "args" in args.keys():
        del args["args"]
    # Get MODIS images
    modisImages = gv.getModisData(startYear, endYear, startJulian, endJulian, daily=True, maskWQA=False, zenithThresh=90, useTempInCloudMask=True, addLookAngleBands=False, resampleMethod="bicubic")

    # Compute cloudScore
    cloudScores = modisImages.map(gv.modisCloudScore)

    # Compute the cloudScore percentiles
    cloudScorePctls = cloudScores.reduce(ee.Reducer.percentile(percentiles))
    Map.addLayer(cloudScorePctls.clip(exportArea), {"min": 0, "max": 30}, "{} Cloud Score pctls".format(name))
    Map.addLayer(modisImages.median().clip(exportArea), gv.vizParamsFalse, "{} Before Masking".format(name))

    # Bust out clouds
    modisImages = gv.applyCloudScoreAlgorithm(modisImages, gv.modisCloudScore, cloudScoreThresh, cloudScorePctl, contractPixels, dilatePixels, performCloudScoreOffset)
    Map.addLayer(modisImages.median().clip(exportArea), gv.vizParamsFalse, "{} After Masking".format(name))

    # Compute TDOM stats
    stdDev = modisImages.select(tdomBands).reduce(ee.Reducer.stdDev())
    mean = modisImages.select(tdomBands).reduce(ee.Reducer.mean())
    count = modisImages.select([0]).reduce(ee.Reducer.count()).rename(["cloudFreeCount"])
    stats = mean.addBands(stdDev).multiply(10000).addBands(cloudScorePctls).addBands(count).int16().setMulti(args)
    stats = ee.Image(stats)
    Map.addLayer(stats.clip(exportArea), {"min": 500, "max": 2000}, "{} TDOM Stats".format(name))

    # Export the output
    outputName = "{}_CS-TDOM-Stats_{}-{}_{}-{}".format(name, startYear, endYear, startJulian, endJulian)
    print(outputName)
    gv.exportToAssetWrapper(stats, outputName, exportPath + "/" + outputName, pyramidingPolicyObject=None, roi=exportArea, scale=None, crs=crs, transform=transform)


####################################################################################################
# Function to get a z score from a given set of imates and dates
def getZ(
    images,
    indexNames,
    startJulian,
    endJulian,
    analysisYear,
    baselineLength=3,
    baselineGap=1,
    zReducer=ee.Reducer.percentile([70]),
    zThresh=-3,
    crs="EPSG:5070",
    transform=[240, 0, -2361915.0, 0, -240, 3177735.0],
    scale=None,
    exportBucket="lamda-raw-outputs",
    exportAreaName="",
    exportArea=None,
    exportRawZ=False,
):
    args = gv.formatArgs(locals())
    if "args" in args.keys():
        del args["args"]
    # print(args)

    current_tasks = tml.getTasks()
    # Filter image dates
    images = images.filter(ee.Filter.calendarRange(startJulian, endJulian))

    # Get baseline images
    baselineStartYear = analysisYear - baselineGap - baselineLength
    baselineEndYear = analysisYear - baselineGap - 1
    baselineImages = images.filter(ee.Filter.calendarRange(baselineStartYear, baselineEndYear, "year"))
    # Map.addLayer(baselineImages.median().reproject(crs,transform,scale),vizParamsFalse,'Baseline Median ay{} jd{}-{}'.format(analysisYear,startJulian,endJulian),False)

    # Compute baseline stats
    baselineMean = baselineImages.select(indexNames).mean()
    baselineStdDev = baselineImages.select(indexNames).reduce(ee.Reducer.stdDev())

    # Get analysis images
    analysisImages = images.filter(ee.Filter.calendarRange(analysisYear, analysisYear, "year"))
    # Map.addLayer(analysisImages.median().reproject(crs,transform,scale),vizParamsFalse,'Analysis Median ay{} jd{}-{}'.format(analysisYear,startJulian,endJulian),False)

    # Compute z scores
    analysisZs = analysisImages.select(indexNames).map(lambda img: (img.subtract(baselineMean)).divide(baselineStdDev))

    # Reduce the z scores across time and then multiple bands (if more than one indexNames is specified)
    analysisZ = analysisZs.reduce(zReducer).reduce(ee.Reducer.min())

    # Threshold z score
    negativeDeparture = analysisZ.lte(zThresh).selfMask()
    # Map.addLayer(negativeDeparture.reproject(crs,transform,scale),{'min':1,'max':1,'palette':'F00'},'Z Negative Departure bl{}-{} ay{} jd{}-{}'.format(baselineStartYear,baselineEndYear,analysisYear,startJulian,endJulian))

    # Set up year date image
    yearImage = ee.Image(analysisYear).add(endJulian / 365.25).float().updateMask(negativeDeparture)

    # Export z score if chosen
    if exportRawZ:
        rawZOutputName = "{}_LAMDA_Z_{}_bl{}-{}_ay{}_jd{}-{}".format(exportAreaName, "-".join(indexNames), baselineStartYear, baselineEndYear, analysisYear, startJulian, endJulian)
        tracking_filenames.append(rawZOutputName)

        forExport = analysisZ.multiply(1000).clamp(-32767, 32767).int16()  # .clamp(-10,10).add(10).multiply(10).byte()#.clamp(-32767,32767).int16()
        # Map.addLayer(forExport,{'min':0,'max':200,'palette':'F00,888,00F'},rawZOutputName)
        # if not csl.gcs_exists(exportBucket, rawZOutputName + ".tif") and rawZOutputName not in current_tasks["ready"] and rawZOutputName not in current_tasks["running"]:
        gv.exportToCloudStorageWrapper(forExport, rawZOutputName, exportBucket, exportArea, scale, crs, transform, outputNoData=-32768, overwrite=False)
        # else:
        #     print(rawZOutputName, " already exists or is in queue to run")
    # Return raw z score and masked year image
    return ee.Image.cat([analysisZ, yearImage]).rename(["Raw_Z", "Year"]).float().set("system:time_start", ee.Date.fromYMD(analysisYear, 1, 1).advance(endJulian, "day").millis()).set(args)


####################################################################################################
# Function to get trend of given images
def getTrend(
    images,
    indexNames,
    startJulian,
    endJulian,
    analysisYear,
    epochLength,
    annualReducer=ee.Reducer.percentile([50]),
    slopeThresh=-0.05,
    crs="EPSG:5070",
    transform=[240, 0, -2361915.0, 0, -240, 3177735.0],
    scale=None,
    exportBucket="lamda-raw-outputs",
    exportAreaName="",
    exportArea=None,
    exportRawSlope=False,
):

    # Find years for specified epoch
    epochStartYear = analysisYear - epochLength + 1
    years = list(range(epochStartYear, analysisYear + 1))
    print("TDD years:", years)

    args = gv.formatArgs(locals())
    if "args" in args.keys():
        del args["args"]
    # print(args)

    current_tasks = tml.getTasks()

    # Filter image dates
    images = images.filter(ee.Filter.calendarRange(startJulian, endJulian))

    # Set up images
    images = images.select(indexNames)
    bns = images.first().bandNames()

    # Convert into annual composites
    composites = ee.ImageCollection([images.filter(ee.Filter.calendarRange(yr, yr, "year")).reduce(annualReducer).set("system:time_start", ee.Date.fromYMD(yr, 1, 1).advance(startJulian, "day").millis()).rename(bns) for yr in years])

    # Get linear fit model and predicted values with said model (from changeDetectionLib)
    model, predicted = gv.getLinearFit(composites)
    predicted = ee.ImageCollection(predicted)

    # Reduce the slope to min of multiple indexNames specified
    slope = model.select([".*slope"]).reduce(ee.Reducer.min())

    # Visualize annual composites and linear fit
    # Map.addLayer(predicted,{'opacity':0},'Actual-Predicted yrs{}-{} jd{}-{}'.format(years[0],years[-1],startJulian,endJulian),False)

    # Threshold trend
    negativeSlope = slope.lte(slopeThresh).selfMask()

    # Set up year image and mask to thresholded slope
    yearImage = ee.Image(analysisYear).add(endJulian / 365.25).float().updateMask(negativeSlope.mask())

    # Export slope if chosen
    if exportRawSlope:
        rawSlopeOutputName = "{}_LAMDA_TDD_{}_yrs{}-{}_jd{}-{}".format(exportAreaName, "-".join(indexNames), years[0], years[-1], startJulian, endJulian)
        tracking_filenames.append(rawSlopeOutputName)

        forExport = slope.multiply(10000).clamp(-32767, 32767).int16()  # .clamp(-0.2,0.2).add(0.2).multiply(500).byte()#.multiply(100000).clamp(-32767,32767).int16()
        # Map.addLayer(forExport,{'min':0,'max':200,'palette':'F00,888,00F'},rawSlopeOutputName)
        # if not gcs_exists(exportBucket, rawSlopeOutputName + ".tif") and rawSlopeOutputName not in current_tasks["ready"] and rawSlopeOutputName not in current_tasks["running"]:
        gv.exportToCloudStorageWrapper(forExport, rawSlopeOutputName, exportBucket, exportArea, scale, crs, transform, outputNoData=-32768, overwrite=False)
        # else:
        #     print(rawSlopeOutputName, " already exists or is in queue to run")

    # Return raw slope and date masked to thresholded slope
    return ee.Image.cat([slope, yearImage]).rename(["Raw_Slope", "Year"]).float().set("system:time_start", ee.Date.fromYMD(analysisYear, 1, 1).advance(endJulian, "day").millis()).set(args)


####################################################################################################
# Wrapper for LAMDA to run z-score and tdd methods
def lamda_wrapper(
    analysisYears,
    startJulians,
    nDays=16,
    zBaselineLength=3,
    tddEpochLength=5,
    baselineGap=1,
    indexNames=["NBR"],
    zThresh=-2.5,
    slopeThresh=-0.05,
    zReducer=ee.Reducer.percentile([60]),
    tddAnnualReducer=ee.Reducer.percentile([50]),
    zenithThresh=90,
    addLookAngleBands=True,
    applyCloudScore=True,
    applyTDOM=True,
    cloudScoreThresh=20,
    performCloudScoreOffset=True,
    cloudScorePctl=10,
    zScoreThresh=-1,
    shadowSumThresh=0.35,
    contractPixels=0,
    dilatePixels=2.5,
    resampleMethod="bicubic",
    preComputedCloudScoreOffset=None,
    preComputedTDOMIRMean=None,
    preComputedTDOMIRStdDev=None,
    treeMask=None,
    crs="EPSG:5070",
    transform=[240, 0, -2361915.0, 0, -240, 3177735.0],
    scale=None,
    exportBucket="lamda-raw-outputs",
    exportAreaName="",
    exportArea=None,
    exportRawZ=False,
    exportRawSlope=False,
):

    # Set up union of all years needed
    startYear = min(analysisYears) - max([tddEpochLength, zBaselineLength]) - baselineGap
    endYear = max(analysisYears)

    # #Pull in lcms data for masking
    # lcms = ee.ImageCollection("USFS/GTAC/LCMS/v2020-5").filter(ee.Filter.calendarRange(startYear,endYear,'year'))
    # lcmsChange = lcms.select(['Change'])
    # lcmsChange = lcmsChange.map(lambda img: img.gte(2).And(img.lte(4))).max().selfMask()
    # lcmsTreeMask = lcms.select(['Land_Cover']).map(lambda img: img.lte(6)).max().selfMask()
    # # Map.addLayer(lcmsChange,{'min':1,'max':1,'palette':'800'},'LCMS Change',False)
    # Map.addLayer(lcmsTreeMask,{'min':1,'max':1,'palette':'080'},'LCMS Trees',False)

    # Find union of julian dates
    startJulian = min(startJulians)
    endJulian = max(startJulians) + nDays - 1

    # Get cloud and cloud shadow busted MODIS images from Aqua and Terra 250, 500, and 1000 m spatial resolution SR collections
    modisImages = gv.getProcessedModis(
        startYear,
        endYear,
        startJulian,
        endJulian,
        zenithThresh=zenithThresh,
        addLookAngleBands=True,
        applyCloudScore=applyCloudScore,
        applyTDOM=applyTDOM,
        useTempInCloudMask=True,
        cloudScoreThresh=cloudScoreThresh,
        performCloudScoreOffset=performCloudScoreOffset,
        cloudScorePctl=cloudScorePctl,
        zScoreThresh=zScoreThresh,
        shadowSumThresh=shadowSumThresh,
        contractPixels=contractPixels,
        dilatePixels=dilatePixels,
        resampleMethod=resampleMethod,
        preComputedCloudScoreOffset=preComputedCloudScoreOffset,
        preComputedTDOMIRMean=preComputedTDOMIRMean,
        preComputedTDOMIRStdDev=preComputedTDOMIRStdDev,
    )
    modisImages = ee.ImageCollection(modisImages)

    # Mask out non trees if specified
    if treeMask != None:
        print("Applying  Tree Mask")
        modisImages = modisImages.map(lambda img: img.updateMask(treeMask))
        Map.addLayer(treeMask, {"min": 1, "max": 1, "palette": "080", "classLegendDict": {"Trees": "080"}}, "Tree Mask", False)
    # Bring in raw images for charting
    Map.addLayer(modisImages.select(indexNames), {"opacity": 0}, "Raw MODIS Time Series", False)

    # Iterate across years and julian periods and run z-score and TDD and export outputs if specified
    # Put outputs into collections for vizualization
    z_collection = []
    tdd_collection = []
    full_year_list = []

    for analysisYear in analysisYears:
        Map.addLayer(modisImages.filter(ee.Filter.calendarRange(analysisYear, analysisYear, "year")).median(), gv.vizParamsFalse, "{} Composite".format(analysisYear), False)
        for startJulian in startJulians:
            endJulian = startJulian + nDays - 1
            full_year_list.append(round(analysisYear + (startJulian / 365.25), 2))
            print("Running LAMDA over: ", analysisYear, startJulian, endJulian)
            z = getZ(modisImages, indexNames, startJulian, endJulian, analysisYear, zBaselineLength, baselineGap, zReducer, zThresh, crs, transform, scale, exportBucket, exportAreaName, exportArea, exportRawZ)

            trend = getTrend(modisImages, indexNames, startJulian, endJulian, analysisYear, tddEpochLength, tddAnnualReducer, slopeThresh, crs, transform, scale, exportBucket, exportAreaName, exportArea, exportRawSlope)

            z_collection.append(z)
            tdd_collection.append(trend)

    z_collection = ee.ImageCollection(z_collection)
    tdd_collection = ee.ImageCollection(tdd_collection)

    lossYearPalette = "ffffe5,fff7bc,fee391,fec44f,fe9929,ec7014,cc4c02"
    lossDurPalette = "0C2780,E2F400,BD1600"
    # Vizualize year of change for z-score and TDD
    Map.addLayer(z_collection.max().select([1]), {"min": min(full_year_list), "max": max(full_year_list), "palette": lossYearPalette}, "Most Recent Z Departure", True)
    # if len(startJulians) > 1:
    # 	Map.addLayer(z_collection.select([1]).count(),{'min':1,'max':len(startJulians),'palette':lossDurPalette},'Count Z Departure',True)

    Map.addLayer(tdd_collection.max().select([1]), {"min": min(full_year_list), "max": max(full_year_list), "palette": lossYearPalette}, "Most Recent Negative Trend", True)
    # if len(startJulians) > 1:
    # Map.addLayer(tdd_collection.select([1]).count(),{'min':1,'max':len(startJulians),'palette':lossDurPalette},'Count Negative Trend',True)
    # Vizualize continuous outputs
    if len(analysisYears) == 1 and len(startJulians) == 1:
        Map.addLayer(ee.Image(z_collection.select([0]).max()), {"min": -3, "max": 2, "palette": "F00,888,00F"}, "Raw Z-score")
        Map.addLayer(ee.Image(tdd_collection.select([0]).max()), {"min": -0.05, "max": 0.02, "palette": "F00,888,00F"}, "Raw Trend")

    else:
        Map.addTimeLapse(z_collection.select([0]).map(lambda img: img), {"min": -3, "max": 2, "palette": "F00,888,00F", "dateFormat": "YYYYMMdd", "advanceInterval": "day"}, "Raw Z-score Time Lapse")
        Map.addTimeLapse(tdd_collection.select([0]).map(lambda img: img), {"min": -0.05, "max": 0.02, "palette": "F00,888,00F", "dateFormat": "YYYYMMdd", "advanceInterval": "day"}, "Raw Trend Time Lapse")

        Map.addLayer(z_collection.select([0]), {"opacity": 0}, "Raw Z-score Time Series", False)
        Map.addLayer(tdd_collection.select([0]), {"opacity": 0}, "Raw Trend Time Series", False)

    # Export outputs if chosen
    strAnalysisYears = [str(i) for i in analysisYears]
    strStartJulians = [str(i) for i in startJulians]

    if exportRawZ or exportRawSlope:
        Map.addLayer(exportArea, {}, "Export Area")
    return tracking_filenames


###############################################################
###############################################################
###############################################################
# Functions to process outputs locally


# Function to bring outputs from GCS to local folder
def sync_outputs(gs_bucket, output_folder, output_filter_strings, gsutil_path="gsutil.cmd"):

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    call = None
    # Track previous commands to speed things up
    copy_done_file = os.path.join(output_folder, ".COPY_FINISHED")
    if os.path.exists(copy_done_file):
        o = open(copy_done_file, "r")
        commands = o.read().split(",")
        o.close()
    else:
        commands = []

    # Run each command provided
    for output_filter_string in output_filter_strings:
        sync_command = "{} -m cp -n -r gs://{}/{} {}".format(gsutil_path, gs_bucket, output_filter_string, output_folder)

        if sync_command not in commands:
            call = subprocess.Popen(sync_command)

            commands.append(sync_command)
        else:
            print("Already ran:", sync_command)
    if call != None:
        while call.poll() == None:
            print("Still syncing")
            time.sleep(5)
    # Log which commands have been run
    # o = open(copy_done_file,'w')
    # o.write(','.join(commands))
    # o.close()


def upload_outputs(exportAreaName, local_folder, gs_bucket, extension, gsutil_path="gsutil.cmd"):
    sync_command = "{} -m cp -n -r {}/{}*.{} gs://{}".format(gsutil_path, local_folder, exportAreaName, extension, gs_bucket)
    print(sync_command)
    call = subprocess.Popen(sync_command)

    if call != None:
        while call.poll() == None:
            print("Still syncing")
            time.sleep(5)


###############################################################
# Function to correct projection, set no data, update stats, and stretch to 8 bit
def post_process_local_outputs(local_output_dir, exportAreaName, crs_dict, post_process_dict):

    # Track files that are already finished
    done_file = os.path.join(local_output_dir, ".{}_POST_PROCESS_DONE".format(exportAreaName))
    if os.path.exists(done_file):
        o = open(done_file)
        done_files = o.read().split(",")
        o.close()
    else:
        done_files = []

    # Iterate across each key provided
    for k in list(post_process_dict.keys()):

        # Filter out raw tifs for given key
        tifs = glob.glob(os.path.join(local_output_dir, "{}*{}*.tif".format(exportAreaName, k)))
        tifs = [i for i in tifs if i.find("8bit") == -1 and i.find("_persistence") == -1]

        # Update projection, no data, and stats for each raw output
        for tif in tifs:
            if tif not in done_files:

                crs_key = os.path.basename(tif).split("_")[0]
                crs = crs_dict[crs_key]
                rpl.update_cog(tif, crs, -32768, update_stats=True, stat_stretch_type="stdDev", stretch_n_stdDev=5)

                done_files.append(tif)

            else:
                print("Already post processed:", tif)

            # Stretch raw to 8 bit
            rpl.stretch_to_8bit(tif, -32768, post_process_dict[k]["scale_factor"], post_process_dict[k]["stretch"], post_process_dict[k]["palette"])
            print()

    # Log files tifhat have been processed
    o = open(done_file, "w")
    o.write(",".join(done_files))
    o.close()


###############################################################
def calc_persistence_wrapper(local_output_dir, exportAreaName, indexNames, year, post_process_dict, persistence_n_periods=3):

    # Iterate across each key provided
    for k in list(post_process_dict.keys()):
        tifs = glob.glob(os.path.join(local_output_dir, "*{}*{}*{}*{}*.tif".format(exportAreaName, k, "-".join(indexNames), year)))
        tifs = [i for i in tifs if i.find("8bit") == -1 and i.find("_persistence") == -1]

        jds = list(set(int(os.path.basename(i).split("_jd")[-1].split("-")[0]) for i in tifs))
        jds.sort()

        jds_persist = jds[persistence_n_periods - 1 :]

        for i, jd_persist in enumerate(jds_persist):
            jds_t = jds[i : i + persistence_n_periods]

            tifs_t = [i for i in tifs if int(os.path.basename(i).split("_jd")[-1].split("-")[0]) in jds_t]
            output_persist = tifs_t[-1].split("_jd")[0] + "_jds{}_persistence.tif".format("-".join([str(i) for i in jds_t]))
            if not os.path.exists(output_persist):
                print(jds_t, len(tifs_t) == persistence_n_periods, output_persist)
                rpl.calc_persistence(tifs_t, output_persist, post_process_dict[k]["scale_factor"], post_process_dict[k]["thresh"])
            else:
                print(output_persist, "already exists")
            # out_jpg = os.path.splitext(output_persist)[0]+ '.jpg'
            # rpl.translate(output_persist,out_jpg)


def convert_to_cog(folder):
    tifs = glob.glob(os.path.join(folder, "*.tif"))
    tifs = [i for i in tifs if os.path.basename(i).find("_cog.tif") == -1]
    for tif in tifs:
        output = os.path.splitext(tif)[0] + "_cog.tif"
        if not os.path.exists(output):
            rpl.translate(tif, output, rpl.cogArgs)


###############################################################
def limitProcesses(processLimit):
    while len(multiprocessing.process.active_children()) > processLimit:
        print(len(multiprocessing.process.active_children()), ":active processes")
        time.sleep(5)


# Function to get the most recent date of available MODIS to run LAMDA up until that date
def get_most_recent_MODIS_date(collection="MODIS/061/MYD09GQ"):
    t = time.localtime()
    d = ee.Date.fromYMD(t[0], t[1], t[2])
    c = ee.ImageCollection(collection).filterDate(d.advance(-2, "month"), d).sort("system:time_start", False)
    return ee.Date(c.first().get("system:time_start")).format("YYYY-DD").getInfo()


###############################################################
def operational_lamda(
    first_run,
    frequency,
    nDays,
    zBaselineLength,
    tddEpochLength,
    baselineGap,
    indexNames,
    zThresh,
    slopeThresh,
    zReducer,
    tddAnnualReducer,
    zenithThresh,
    addLookAngleBands,
    applyCloudScore,
    applyTDOM,
    cloudScoreThresh,
    performCloudScoreOffset,
    cloudScorePctl,
    zScoreThresh,
    shadowSumThresh,
    contractPixels,
    dilatePixels,
    resampleMethod,
    preComputedCloudScoreOffset,
    preComputedTDOMIRMean,
    preComputedTDOMIRStdDev,
    tree_mask,
    crs,
    transform,
    scale,
    exportBucket,
    exportAreaName,
    exportArea,
    exportRawZ,
    exportRawSlope,
    local_output_dir,
    gsutil_path,
    crs_dict,
    post_process_dict,
    persistence_n_periods,
    deliverable_output_bucket,
):
    most_recent_modis = get_most_recent_MODIS_date()
    year = int(most_recent_modis.split("-")[0])  # time.localtime()[0]
    jd = int(most_recent_modis.split("-")[1]) - nDays  # time.localtime()[7]
    startJulians = list(range(first_run, jd + 1, frequency))

    # Run LAMDA GEE portion (get MODIS, cloud cloud shadow bust, make raw Z score and trend products)
    tracking_filenames = lamda_wrapper(
        [year],
        startJulians,
        nDays,
        zBaselineLength,
        tddEpochLength,
        baselineGap,
        indexNames,
        zThresh,
        slopeThresh,
        zReducer,
        tddAnnualReducer,
        zenithThresh,
        addLookAngleBands,
        applyCloudScore,
        applyTDOM,
        cloudScoreThresh,
        performCloudScoreOffset,
        cloudScorePctl,
        zScoreThresh,
        shadowSumThresh,
        contractPixels,
        dilatePixels,
        resampleMethod,
        preComputedCloudScoreOffset,
        preComputedTDOMIRMean,
        preComputedTDOMIRStdDev,
        tree_mask,
        crs,
        transform,
        scale,
        exportBucket,
        exportAreaName,
        exportArea,
        exportRawZ,
        exportRawSlope,
    )

    # Wait until exports are finished to proced
    tml.trackTasks2(id_list=tracking_filenames)
    print(tracking_filenames, "finished exporting")

    # Copy outputs to local folder
    output_filter_strings = ["*{}_LAMDA_Z_{}_*_ay{}*".format(exportAreaName, "-".join(indexNames), year), "*{}_LAMDA_TDD_{}_yrs*-{}*".format(exportAreaName, "-".join(indexNames), year)]
    sync_outputs(exportBucket, local_output_dir, output_filter_strings, gsutil_path)

    # Correct crs, no data, and convert to 8 bit
    post_process_local_outputs(local_output_dir, exportAreaName, crs_dict, post_process_dict)

    # Compute persistence
    calc_persistence_wrapper(local_output_dir, exportAreaName, indexNames, year, post_process_dict, persistence_n_periods)

    # #Upload outputs
    upload_outputs(exportAreaName, local_output_dir, deliverable_output_bucket, "tif")
    upload_outputs(exportAreaName, local_output_dir, deliverable_output_bucket, "jpg")

    # Ingest as COG-backed assets
    rc.ingest_lamda()

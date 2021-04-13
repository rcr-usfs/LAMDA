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
#Script to run the Real Time Forest Disturbance (RTFD) Mapper in Google Earth Engine
#This method is a pixel-wise adaptation of the original RTFD algorithms
#Intended to work within the geeViz package
####################################################################################################
from geeViz.changeDetectionLib import *
####################################################################################################
#Function to get a z score from a given set of imates and dates
def getZ(images,indexNames,startJulian,endJulian,analysisYear,baselineLength = 3,baselineGap = 1,zReducer = ee.Reducer.percentile([70]),zThresh = -3,crs = 'EPSG:5070',transform = [240,0,-2361915.0,0,-240,3177735.0],scale = None,exportBucket = 'rtfd-scratch',exportArea = None,exportRawZ = False):
	args = formatArgs(locals())
	if 'args' in args.keys():
		del args['args']
	print(args)

	#Filter image dates
	images = images.filter(ee.Filter.calendarRange(startJulian,endJulian))

	#Get baseline images
	baselineStartYear = analysisYear-baselineGap-baselineLength
	baselineEndYear = analysisYear-baselineGap -1
	baselineImages = images.filter(ee.Filter.calendarRange(baselineStartYear,baselineEndYear,'year'))
	# Map.addLayer(baselineImages.median().reproject(crs,transform,scale),vizParamsFalse,'Baseline Median ay{} jd{}-{}'.format(analysisYear,startJulian,endJulian),False)

	#Compute baseline stats
	baselineMean = baselineImages.select(indexNames).mean()
	baselineStdDev = baselineImages.select(indexNames).reduce(ee.Reducer.stdDev())

	#Get analysis images
	analysisImages = images.filter(ee.Filter.calendarRange(analysisYear,analysisYear,'year'))
	# Map.addLayer(analysisImages.median().reproject(crs,transform,scale),vizParamsFalse,'Analysis Median ay{} jd{}-{}'.format(analysisYear,startJulian,endJulian),False)


	
	#Compute z scores
	analysisZs =  analysisImages.select(indexNames).map(lambda img: img.subtract(baselineMean).divide(baselineStdDev))

	#Reduce the z scores across time and then multiple bands (if more than one indexNames is specified)
	analysisZ = analysisZs.reduce(zReducer).reduce(ee.Reducer.min())

	#Threshold z score
	negativeDeparture = analysisZ.lte(zThresh).selfMask()
	# Map.addLayer(negativeDeparture.reproject(crs,transform,scale),{'min':1,'max':1,'palette':'F00'},'Z Negative Departure bl{}-{} ay{} jd{}-{}'.format(baselineStartYear,baselineEndYear,analysisYear,startJulian,endJulian))

	#Set up year date image
	yearImage = ee.Image(analysisYear).add(endJulian/365.25).float().updateMask(negativeDeparture)

	#Export z score if chosen
	if exportRawZ:
		rawZOutputName = 'RTFD_Z_{}_bl{}-{}_ay{}_jd{}-{}'.format('-'.join(indexNames),baselineStartYear,baselineEndYear,analysisYear,startJulian,endJulian)
		print(rawZOutputName)
		forExport = analysisZ.multiply(1000).clamp(-32767,32767).int16()
		# Map.addLayer(forExport.clip(exportArea).unmask(-32768),{'min':-3000,'max':2000,'palette':'F00,888,00F'},rawZOutputName)
		exportToCloudStorageWrapper(forExport,rawZOutputName,exportBucket,exportArea,scale,crs,transform,outputNoData = -32768)

	#Return raw z score and masked year image
	return ee.Image.cat([analysisZ,yearImage]).rename(['Raw_Z','Year']).float()\
	.set('system:time_start',ee.Date.fromYMD(analysisYear,1,1).advance(endJulian,'day').millis()).set(args)

####################################################################################################
#Function to get trend of given images
def getTrend(images,indexNames,startJulian,endJulian,analysisYear,epochLength,annualReducer = ee.Reducer.percentile([50]),slopeThresh = -0.05,crs = 'EPSG:5070',transform = [240,0,-2361915.0,0,-240,3177735.0],scale = None,exportBucket = 'rtfd-scratch',exportArea = None,exportRawSlope = False):
	
	#Find years for specified epoch
	epochStartYear = analysisYear-epochLength+1
	years = list(range(epochStartYear,analysisYear+1))
	print('TDD years:',years)

	args = formatArgs(locals())
	if 'args' in args.keys():
		del args['args']
	print(args)

	#Set up images
	images = images.select(indexNames)
	bns = images.first().bandNames()
	
	#Convert into annual composites
	composites = ee.ImageCollection([images.filter(ee.Filter.calendarRange(yr,yr,'year')).reduce(annualReducer).set('system:time_start',ee.Date.fromYMD(yr,1,1).advance(startJulian,'day').millis()).rename(bns) for yr in years])

	#Get linear fit model and predicted values with said model (from changeDetectionLib)
	model,predicted = getLinearFit(composites)
	predicted = ee.ImageCollection(predicted)

	#Reduce the slope to min of multiple indexNames specified
	slope = model.select(['.*slope']).reduce(ee.Reducer.min())
	
	#Visualize annual composites and linear fit
	# Map.addLayer(predicted,{'opacity':0},'Actual-Predicted yrs{}-{} jd{}-{}'.format(years[0],years[-1],startJulian,endJulian),False)

	#Threshold trend
	negativeSlope = slope.lte(slopeThresh).selfMask()

	#Set up year image and mask to thresholded slope
	yearImage = ee.Image(analysisYear).add(endJulian/365.25).float().updateMask(negativeSlope.mask())

	#Export slope if chosen
	if exportRawSlope:
		rawSlopeOutputName = 'RTFD_TDD_{}_yrs{}-{}_jd{}-{}'.format('-'.join(indexNames),years[0],years[-1],startJulian,endJulian)
		print(rawSlopeOutputName)
		forExport = slope.multiply(100000).clamp(-32767,32767).int16()
		# Map.addLayer(forExport.clip(exportArea).unmask(-32768),{'min':-5000,'max':2000,'palette':'F00,888,00F'},rawSlopeOutputName)
		exportToCloudStorageWrapper(forExport,rawSlopeOutputName,exportBucket,exportArea,scale,crs,transform,outputNoData = -32768)

	#Return raw slope and date masked to thresholded slope
	return ee.Image.cat([slope,yearImage]).rename(['Raw_Slope','Year']).float()\
	.set('system:time_start',ee.Date.fromYMD(analysisYear,1,1).advance(endJulian,'day').millis()).set(args)


####################################################################################################
#Wrapper for rtfd to run z-score and tdd methods
def rtfd_wrapper(analysisYears, startJulians, nDays = 16, zBaselineLength = 3, tddEpochLength = 5, baselineGap = 1, indexNames = ['NBR'],zThresh = -2.5,slopeThresh = -0.05, zReducer = ee.Reducer.percentile([60]),tddAnnualReducer = ee.Reducer.percentile([50]),\
	zenithThresh = 90,addLookAngleBands = True,applyCloudScore = True, applyTDOM = True, cloudScoreThresh = 20,performCloudScoreOffset = True,cloudScorePctl = 10, zScoreThresh = -1, shadowSumThresh = 0.35, contractPixels = 0,dilatePixels = 2.5,resampleMethod = 'bicubic',preComputedCloudScoreOffset = None,preComputedTDOMIRMean = None,preComputedTDOMIRStdDev = None,\
	applyLCMSTreeMask = True,
	crs = 'EPSG:5070',transform = [240,0,-2361915.0,0,-240,3177735.0],scale = None,exportBucket = 'rtfd-scratch',exportArea = None,exportRawZ = False,exportRawSlope = False):

	#Set up union of all years needed
	startYear = min(analysisYears) - max([tddEpochLength,zBaselineLength]) - baselineGap
	endYear = max(analysisYears)
	
	#Pull in lcms data for masking
	lcms = ee.ImageCollection("USFS/GTAC/LCMS/v2020-5").filter(ee.Filter.calendarRange(startYear,endYear,'year'))
	lcmsChange = lcms.select(['Change'])
	lcmsChange = lcmsChange.map(lambda img: img.gte(2).And(img.lte(4))).max().selfMask()
	lcmsTreeMask = lcms.select(['Land_Cover']).map(lambda img: img.lte(6)).max().selfMask()
	# Map.addLayer(lcmsChange,{'min':1,'max':1,'palette':'800'},'LCMS Change',False)
	Map.addLayer(lcmsTreeMask,{'min':1,'max':1,'palette':'080'},'LCMS Trees',False)

	#Find union of julian dates
	startJulian = min(startJulians)
	endJulian = max(startJulians)+nDays-1

	#Get cloud and cloud shadow busted MODIS images from Aqua and Terra 250, 500, and 1000 m spatial resolution SR collections
	modisImages = getProcessedModis(startYear,
							endYear,
							startJulian,
							endJulian,
							zenithThresh = zenithThresh,
							addLookAngleBands = True,
							applyCloudScore = applyCloudScore,
							applyTDOM = applyTDOM,
							useTempInCloudMask = True,
							cloudScoreThresh = cloudScoreThresh,
							performCloudScoreOffset = performCloudScoreOffset,
							cloudScorePctl = cloudScorePctl,
							zScoreThresh = zScoreThresh,
							shadowSumThresh = shadowSumThresh,
							contractPixels = contractPixels,
							dilatePixels = dilatePixels,
							resampleMethod = resampleMethod,
							preComputedCloudScoreOffset = preComputedCloudScoreOffset,
							preComputedTDOMIRMean = preComputedTDOMIRMean,
							preComputedTDOMIRStdDev = preComputedTDOMIRStdDev)
	modisImages = ee.ImageCollection(modisImages)

	#Mask out non trees if specified
	if applyLCMSTreeMask:
		print('Applying LCMS Tree Mask')
		modisImages = modisImages.map(lambda img: img.updateMask(lcmsTreeMask))

	#Bring in raw images for charting
	Map.addLayer(modisImages.select(indexNames),{'opacity':0},'Raw MODIS Time Series',False)

	#Iterate across years and julian periods and run z-score and TDD and export outputs if specified
	#Put outputs into collections for vizualization
	z_collection = []
	tdd_collection = []
	full_year_list = []
	for analysisYear in analysisYears:
		for startJulian in startJulians:
			endJulian = startJulian + nDays-1
			full_year_list.append(round(analysisYear+(startJulian/365.25),2))
			print('Running RTFD over: ',analysisYear,startJulian,endJulian)
			z = getZ(modisImages,indexNames,startJulian,endJulian,analysisYear,zBaselineLength,baselineGap,zReducer,zThresh,crs,transform,scale,exportBucket,exportArea,exportRawZ)

			trend = getTrend(modisImages,indexNames,startJulian,endJulian,analysisYear,tddEpochLength,tddAnnualReducer,slopeThresh,crs,transform,scale,exportBucket,exportArea,exportRawSlope)
			
			z_collection.append(z)
			tdd_collection.append(trend)
			


	z_collection = ee.ImageCollection(z_collection)
	tdd_collection = ee.ImageCollection(tdd_collection)
	
	lossYearPalette = 'ffffe5,fff7bc,fee391,fec44f,fe9929,ec7014,cc4c02'
	lossDurPalette = '0C2780,E2F400,BD1600'
	#Vizualize year of change for z-score and TDD
	Map.addLayer(z_collection.max().select([1]).reproject(crs,transform,scale),{'min':min(full_year_list),'max':max(full_year_list),'palette':lossYearPalette},'Most Recent Z Departure',True)
	if len(startJulians) > 1:
		Map.addLayer(z_collection.select([1]).count().reproject(crs,transform,scale),{'min':1,'max':len(startJulians),'palette':lossDurPalette},'Count Z Departure',True)

	Map.addLayer(tdd_collection.max().select([1]).reproject(crs,transform,scale),{'min':min(full_year_list),'max':max(full_year_list),'palette':lossYearPalette},'Most Recent Negative Trend',True)
	if len(startJulians) > 1:
		Map.addLayer(tdd_collection.select([1]).count().reproject(crs,transform,scale),{'min':1,'max':len(startJulians),'palette':lossDurPalette},'Count Negative Trend',True)
	#Vizualize continuous outputs
	if len(analysisYears) == 1 and len(startJulians) == 1:
		Map.addLayer(ee.Image(z_collection.select([0]).max()).reproject(crs,transform,scale),{'min':-3,'max':2,'palette':'F00,888,00F'},'Raw Z-score')
		Map.addLayer(ee.Image(tdd_collection.select([0]).max()).reproject(crs,transform,scale),{'min':-0.05,'max':0.02,'palette':'F00,888,00F'},'Raw Trend')

	else:
		Map.addTimeLapse(z_collection.select([0]).map(lambda img:img.reproject(crs,transform,scale)),{'min':-3,'max':2,'palette':'F00,888,00F','dateFormat':'YYYYMMdd','advanceInterval':'day'},'Raw Z-score Time Lapse')
		Map.addTimeLapse(tdd_collection.select([0]).map(lambda img:img.reproject(crs,transform,scale)),{'min':-0.05,'max':0.02,'palette':'F00,888,00F','dateFormat':'YYYYMMdd','advanceInterval':'day'},'Raw Trend Time Lapse')
		
		Map.addLayer(z_collection.select([0]),{'opacity':0},'Raw Z-score Time Series',False)
		Map.addLayer(tdd_collection.select([0]),{'opacity':0},'Raw Trend Time Series',False)

	#Visualize legacy RTFD outputs
	i1 = ee.ImageCollection('projects/gtac-rtfd/assets/GEE-Migration/testImages').mosaic()
	i1 = i1.selfMask()
	Map.addLayer(i1,{'min':75,'max':150,'palette':'F00,888,00F'},'Original RTFD 185-200',False)

	if exportRawZ or exportRawSlope:
		Map.addLayer(exportArea,{},'Export Area')


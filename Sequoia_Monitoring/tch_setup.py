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

# Setup TCH in GEE
####################################################################################################
import os,sys,glob,rasterio,json,numpy
import geeViz.getImagesLib as getImagesLib
import geeViz.taskManagerLib as tml
import geeViz.assetManagerLib as aml
ee = getImagesLib.ee
Map = getImagesLib.Map
Map.clearMap()
####################################################################################################
crs = 'EPSG:32611'#'EPSG:5070'
transform = [10,0,-2361915.0,0,-10,3177735.0]
scale = None
bucket = 'gs://lamda-sequoia-monitoring-inputs'
tch_local_folder = 'Q:/LAMDA_workspace/giant-sequoia-monitoring/Inputs/SEQU_all/SEQU_all'
tch_asset_collection = 'projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/TCH'
####################################################################################################
# Function to ingest TCH tifs as a GEE asset
def uploadTCH(uploadRaw = False,uploadExtracts=True):
    def getnoData(img):
        with rasterio.open(img) as src:
            # raster_data = src.read(1)
            nodata_value = src.nodata 
        return nodata_value
    extract_tifs = glob.glob(os.path.join(tch_local_folder,'*_extract_gfch.tif'))
    print(extract_tifs)
    forest_tifs = glob.glob(os.path.join(tch_local_folder,'*_forest.tif'))
    if uploadExtracts:
        for extract_tif in extract_tifs:
            nodata_value = getnoData(extract_tif)
            baseName = os.path.splitext(os.path.basename(extract_tif))[0]
            assetPath = tch_asset_collection+'/'+baseName
            startYear = int(baseName.split('_')[2])
            endYear = int(baseName.split('_')[3])
        
            aml.uploadToGEEImageAsset(extract_tif,bucket,assetPath,overwrite = False,bandNames = ['TCH_Count'],properties = {'startYear':startYear,'endYear':endYear,'system:time_start':ee.Date.fromYMD(startYear,6,1)},pyramidingPolicy='MODE',noDataValues=nodata_value)
    if uploadRaw:
        for forest_tif in forest_tifs:
            nodata_value = getnoData(forest_tif)
            baseName = os.path.splitext(os.path.basename(forest_tif))[0]
            assetPath = tch_asset_collection+'/'+baseName
            year = int(baseName.split('_')[2])
            print(nodata_value)
            aml.uploadToGEEImageAsset(forest_tif,bucket,assetPath,overwrite = False,bandNames = ['TCH_Class'],properties = {'year':year,'system:time_start':ee.Date.fromYMD(year,6,1)},pyramidingPolicy='MODE',noDataValues=nodata_value)
    tml.trackTasks2()
####################################################################################################
# Viewing TCH
extracted_names = ['Green->Green','Green->Red','Green->Gray','Red->Gray']
extracted_colors = ['080','800','888','F88']
extracted_min = 1
extracted_max = 4
extractedLegendDict =dict(zip(extracted_names,extracted_colors))
extractedQueryDict = dict(zip(range(extracted_min,extracted_max+1),extracted_names))

tch_names = ['Red','Gray','Green','Shadow']
tch_colors = ['F00','888','080','000']
tch_min = 1
tch_max = 4
tchLegendDict =dict(zip(tch_names,tch_colors))
tchQueryDict = dict(zip(range(tch_min,tch_max+1),tch_names))

tch_year_pairs = [[2018,2020],[2020,2022]]

rawViz={'min':tch_min,'max':tch_max,'palette':tch_colors,'classLegendDict':tchLegendDict,'queryDict':tchQueryDict}
extractedViz={'min':extracted_min,'max':extracted_max,'palette':extracted_colors,'classLegendDict':extractedLegendDict,'queryDict':extractedQueryDict}
####################################################################################################
# Function to view GEE asset TCH outputs
def viewTCH(Map,studyArea):
    tch = ee.ImageCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/TCH');
    extracted = tch.filter(ee.Filter.stringContains('system:index','extract_gfch'));
    raw = tch.filter(ee.Filter.stringContains('system:index','extract_gfch').Not());
    naip = ee.ImageCollection("USDA/NAIP/DOQQ").filterBounds(studyArea).select([0,1,2],['R','G','B']);
    extracted_years = extracted.aggregate_histogram('startYear').keys().getInfo()
    raw_years = [int(float(n)) for n in raw.aggregate_histogram('year').keys().getInfo()]
    print(raw_years,extracted_years)
    
    
    for yr in raw_years:
        img = raw.filter(ee.Filter.eq('year',yr)).first();
        naipYr = naip.filter(ee.Filter.calendarRange(yr,yr,'year'))
        # dates = naipYr.toList(10,0).map(lambda img:ee.Image(img).date().format('YYYY-MM-dd')).getInfo()
        # print(yr,dates)
        naipYr=naipYr.mosaic()
        extractedImg = extracted.filter(ee.Filter.eq('endYear',yr))
        extractStartYear = yr-2
        Map.addLayer(naipYr,{'min':25,'max':225},'NAIP {}'.format(yr),False)
        Map.addLayer(img,rawViz,'Raw TCH {}'.format(yr),False)
        l = extractedImg.size().getInfo()
        if l>0:
            Map.addLayer(extractedImg.first(),extractedViz,'Extract GFCH {}-{}'.format(extractStartYear,yr),False)
        
tchC = ee.ImageCollection('projects/gtac-lamda/assets/giant-sequoia-monitoring/Inputs/TCH')  
def getTCHExtract(startYear,endYear,filterString= 'v3shadows_extract_gfch'):
    return tchC.filter(ee.Filter.stringContains('system:index',filterString))\
    .filter(ee.Filter.eq('startYear',startYear))\
    .filter(ee.Filter.eq('endYear',endYear)).first()

def convert_to_csv(output_table_name):
    output_csv = os.path.splitext(output_table_name)[0] + '.csv'
    with open(output_table_name) as jf:
        table = json.load(jf)

        bands = list(table['features'][0]['properties'].keys())
        header = ','.join(bands)+'\n'
        out = header
        
        for feature in table['features']:
            props = feature['properties']
            values = numpy.array(list(props.values()))
            # values[values==None]=''
            values = ','.join([str(i) for i in values])+'\n'
            out+=values
        
        o = open(output_csv,'w')
        o.write(out)
        o.close()

####################################################################################################
if __name__ == '__main__':
    uploadTCH(uploadRaw = False,uploadExtracts=True)
# View map
# Map.centerObject(past_mortality)
# Map.setQueryCRS(crs)
# Map.setQueryTransform(transform)
# Map.turnOnInspector()
# Map.view()

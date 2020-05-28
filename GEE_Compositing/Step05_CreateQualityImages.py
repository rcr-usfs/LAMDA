################################################################################
#                                                                              #
#  Author:                                                                     #
#                                                                              #
#  Bonnie Ruefenacht, PhD                                                      #
#  Senior Specialist                                                           #
#  RedCastle Resources, Inc.                                                   #
#  Working onsite at:                                                          #
#  USDA Forest Service                                                         #
#  Remote Sensing Applications Center (RSAC)                                   #
#  2222 West 2300 South                                                        #
#  Salt Lake City, UT 84119                                                    #
#  Office: (801) 975-3828                                                      #
#  Mobile: (801) 694-9215                                                      #
#  Email: bruefenacht@fs.fed.us                                                #
#  RSAC FS Intranet website: http://fsweb.rsac.fs.fed.us/                      #
#  RSAC FS Internet website: http://www.fs.fed.us/eng/rsac/                    #
#                                                                              #
#  Purpose:                                                                    #
#                                                                              #
#  Sums the three quality files: qualbands124, qual_ndvi, and qual_focal_sd.   #
#                                                                              #
#  This script is called from the MODIS_Compositing.py script.                 #
#                                                                              #
################################################################################
#                                                                              #
#  IMPORT PYTHON MODULES                                                       #
#                                                                              #
################################################################################

import os, pp, glob, time

################################################################################
#                                                                              #
#  IMPORT CUSTOM PYTHON MODULES                                                #
#                                                                              #
#  AssignProcessesToCPUs: used to assign processes to individual processors    #
#  CheckLogFiles: Checks .log files for errors                                 # 
#  CreateBatFiles: Used to create ERDAS formatted DOS bat files                #
#  GetFilenameParts: used to reformat a filename                               #
#  RunZoneBatchFiles: used to run the DOS bat files                            #
#  TimeString: used to get and format the current time for printing purposes   #
#                                                                              #
################################################################################

from AssignProcessesToCPUs import GetFileDict
from CheckLogFiles import CheckLogFiles
from CreateBatFiles import CreateBatFile
from GetFilenameParts import FilenameParts
from RunZoneBatchFiles import RunBatchFile
from TimeString import TimeString

################################################################################
#                                                                              #
#  VARIABLE DESCRIPTIONS                                                       #
#                                                                              #
#******************************************************************************#
#                                                                              #
#  SCRIPT DEFINED VARIABLES                                                    #
#                                                                              #
#  COMPOSITEDATE: starting comosite day                                        #
#  COMPOSITEDIRECTORIES: the working composing directory for each satellite    #
#  IMAGERYLIST: dictionary of satellite images:                                #
#                 IMAGERYLIST[satellite][zone][day] = list of images           #
#  ZONE_COORDINANTES: bounding boxes for the zones                             #
#                                                                              #
#******************************************************************************#
#                                                                              #
#  USER DEFINED VARIABLES                                                      #
#                                                                              #
#  AOI_DIRECTORY: directory containing aois for the zones                      #
#  NCPUS: number of CPUs available for processing                              #
#  NUMBER_OF_COMPOSITE_DAYS: number of days in the compositing period          #
#  SATELLITE: type of satellite sensor (i.e., AQUA, TERRA)                     #
#  ZONES: list of zones to process                                             #
#                                                                              #
#******************************************************************************#
#                                                                              #
#  OPTIONAL VARIABLES                                                          #
#                                                                              #
#  HTML_LINES: Python dictionary where the keys are the names of the           #
#              satellites (TERRA, AQUA). The values of the dictionary keys are #
#              lists of HTML text that are written to html files that informs  #
#              the users what the program is doing.                            #
#                                                                              #
################################################################################

AOI_DIRECTORY = 'W:/AOI'
NCPUS = int(os.environ['NUMBER_OF_PROCESSORS'])
NUMBER_OF_COMPOSITE_DAYS = 16
SATELLITE = ['TERRA','AQUA']
ZONES = {}
for satellite in SATELLITE:
    ZONES[satellite] = ['zone01','zone02','zone03','zone04','zone05','zone06','zone07','zone08','zone09','zone10','zone11','zone12','zone13','zone14']

COMPOSITEDATE = -1
COMPOSITEDIRECTORIES = {}
IMAGERYLIST = {}
ZONE_COORDINANTES = {}

HTML_LINES = {}

LOG = 'W:/scripts/Logs/log_' + str(time.localtime()[7]) + '.txt'

################################################################################
#                                                                              #
#  Function: CalcQualityFiles                                                  #
#                                                                              #
#  Function Purpose:                                                           #
#                                                                              #
#  Create a model (MDL file) that sums the three quality files: qualbands124,  #
#  qual_ndvi, and qual_focal_sd.                                               #
#                                                                              #
#  Example of MDL:                                                             #
#                                                                              #
#       SET CELLSIZE MIN;
#       SET WINDOW -2300790.75, 3177123.75 : -1526129.63, 2243694.75 MAP;
#       SET AOI "W:/AOI/zone01.aoi";
#       integer raster zone01_quality file new ignore 0 thematic bin direct default 16 bit unsigned integer "W:/TERRA/composites/2011/049_064/zone01_path_crefl1mod03_A2011049183118_2011049184329_quality.img";
#       integer raster zone01_qual_ndvi file old nearest neighbor aoi none "W:/TERRA/composites/2011/049_064/zone01_path_crefl1mod03_A2011049183118_2011049184329_qual_ndvi.img";
#       integer raster zone01_qual_focal_sd file old nearest neighbor aoi none "W:/TERRA/composites/2011/049_064/zone01_path_crefl1mod03_A2011049183118_2011049184329_qual_focal_sd.img";
#       integer raster zone01_qual_bands124 file old nearest neighbor aoi none "W:/TERRA/composites/2011/049_064/path_crefl1mod03_A2011049183118_2011049184329_qual_bands124.img";
#       integer raster zone01_noimage_mask file old nearest neighbor aoi none "W:/TERRA/composites/2011/049_064/path_crefl1mod03_A2011049183118_2011049184329_noimage_mask.img";
#       zone01_quality = either $zone01_noimage_mask * ( $zone01_qual_ndvi + $zone01_qual_focal_sd + $zone01_qual_bands124 ) if ( $zone01_qual_ndvi != 0 &&  $zone01_qual_focal_sd != 0 ) or 0 otherwise ;
#       quit;
#                                                                              #
################################################################################

def CalcQualityFiles(satellite,zone):

    # List of .bat files.
    BatFilesList = []

    # A zone must have more than 2 images.
    if (IMAGERYLIST[satellite][zone]['TotalImages'] >= 3):

        # For every images, create a quality image.
        for Date in range (COMPOSITEDATE, COMPOSITEDATE + NUMBER_OF_COMPOSITE_DAYS):
            for MODISSwathImage in IMAGERYLIST[satellite][zone][Date]:
                filename = zone + '_' + FilenameParts(MODISSwathImage)

                # Check if the output image does not exist and the AOI does exist.
                OutputImage = COMPOSITEDIRECTORIES[satellite].replace('\\','/') + '/' + filename + '_quality.img'
                AOI = AOI_DIRECTORY.replace('\\','/') + '/' + zone + '.aoi'
                if (os.path.exists(OutputImage) == False) & (os.path.exists(AOI)):

                    # Create the model.
                    ModelText = []
                    ModelText.append('SET CELLSIZE MIN;\n')
                    ModelText.append(ZONE_COORDINANTES[zone])
                    ModelText.append('SET AOI "' + AOI + '";\n')
                    ModelText.append('\n')
                    ModelText.append('integer raster ' + filename + '_quality file new ignore 0 thematic bin direct default 16 bit unsigned integer "' + OutputImage + '";\n\n')
                    ModelText.append('integer raster ' + filename + '_qual_ndvi file old nearest neighbor aoi none "' + COMPOSITEDIRECTORIES[satellite].replace('\\','/') + '/' + filename + '_qual_ndvi.img";\n')
                    ModelText.append('integer raster ' + filename + '_qual_focal_sd file old nearest neighbor aoi none "' + COMPOSITEDIRECTORIES[satellite].replace('\\','/') + '/' + filename + '_qual_focal_sd.img";\n')
                    ModelText.append('integer raster ' + filename + '_qual_bands124 file old nearest neighbor aoi none "' + COMPOSITEDIRECTORIES[satellite].replace('\\','/') + '/' + FilenameParts(MODISSwathImage) + '_qual_bands124.img";\n')
                    ModelText.append('integer raster ' + filename + '_noimage_mask file old nearest neighbor aoi none "' + COMPOSITEDIRECTORIES[satellite].replace('\\','/') + '/' + FilenameParts(MODISSwathImage) + '_noimage_mask.img";\n')
                    ModelText.append('\n')
                    ModelText.append(filename + '_quality = either $' + filename + '_noimage_mask * ( $' + filename + '_qual_ndvi + $' + filename + '_qual_focal_sd + $' + filename + '_qual_bands124 ) if ( $' + filename + '_qual_ndvi != 0 &&  $' + filename + '_qual_focal_sd != 0 ) or 0 otherwise ;\n\n')
                    ModelText.append('quit;\n')

                    # Create the .bat file.
                    BatFilesList.append([CreateBatFile(COMPOSITEDIRECTORIES[satellite].replace('\\','/'), filename + '_quality',ModelText),[OutputImage]])
    return BatFilesList

################################################################################
#                                                                              #
#  Function: Run                                                               #
#                                                                              #
################################################################################

def Run():
    global HTML_Lines_Changed

    FINALCHECK = False
    HTML_Lines_Changed = False

    ############################################################################
    #                                                                          #
    #  Get a list of bat files.                                                #
    #                                                                          #
    ############################################################################

    BatFiles = {}
    TotalNumberOfFiles = 0
    for satellite in SATELLITE:
        BatFiles[satellite] = {}
        for zone in ZONES[satellite]:
            BatFiles[satellite][zone] = CalcQualityFiles(satellite,zone)
            TotalNumberOfFiles = TotalNumberOfFiles + len(BatFiles[satellite][zone])
    
    print TimeString(),'-> Step 5 - Creating Band Quality Images: Running',TotalNumberOfFiles,'Processes'
    LogOutput = open(LOG,'a')
    LogOutput.write(TimeString() + ' -> Step 5 - Creating Band Quality Images: Running ' + str(TotalNumberOfFiles) + ' Processes\n')
    LogOutput.close()
    
    count = 0
    while (count < 10) & (TotalNumberOfFiles > 0):
        count = count + 1
        
        HTML_Lines_Changed = True

        ########################################################################
        #                                                                      #
        #  Write stuff to HTML                                                 #
        #                                                                      #
        ########################################################################
        
        for satellite in SATELLITE:
            if (HTML_LINES.get(satellite) == None):
                HTML_LINES[satellite] = []
                HTML_LINES[satellite].append("<body>\n")
                HTML_LINES[satellite].append("<div>\n")

            if (count > 1):
                HTML_LINES[satellite].append("</ul>\n")
                HTML_LINES[satellite].append("</dl>\n")

            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<dl>\n")
            HTML_LINES[satellite].append("<dt><b>Step 5: Creating Quality Images</b></dt>\n")

            HTML_LINES[satellite].append("<p></p>\n")
            LogOutput = open(LOG,'a')
            for zone in ZONES[satellite]:
                HTML_LINES[satellite].append("<dd>" + TimeString() + " -> " + zone + " Processing " + str(len(BatFiles[satellite][zone])) + " Files</dd>\n")
                print TimeString(),'->',zone,'processing',len(BatFiles[satellite][zone])
                LogOutput.write(TimeString() + ' -> ' + zone + ' processing ' + str(len(BatFiles[satellite][zone])) + '\n')
            LogOutput.close()
            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<ul>\n")

        ########################################################################
        #                                                                      #
        #  Assign processes to the CPUs                                        #
        #                                                                      #
        ########################################################################

        List = []
        for satellite in SATELLITE:
            for zone in ZONES[satellite]:
                if (IMAGERYLIST[satellite][zone]['TotalImages'] >= 3):
                    List.append([satellite,zone])
        ZoneDict = GetFileDict(NCPUS,List)

        ########################################################################
        #                                                                      #
        #  Run the process                                                     #
        #                                                                      #
        ########################################################################
            
        job_server = pp.Server()
        [job_server.submit(RunBatchFile, (ZoneDict[cpu],BatFiles),(),('subprocess','os')) for cpu in range(1,NCPUS+1)]
        job_server.wait()
        job_server.print_stats()
        job_server.destroy()

        ########################################################################
        #                                                                      #
        #  Check the log files for errors.                                     #
        #                                                                      #
        ########################################################################

        for satellite in SATELLITE:
            for zone in ZONES[satellite]:
                New_HTML_LINES = CheckLogFiles(satellite,COMPOSITEDIRECTORIES,zone + '*_quality.log',FINALCHECK)
            HTML_LINES[satellite].extend(New_HTML_LINES[satellite])

        ########################################################################
        #                                                                      #
        #  Get a list of bat files.                                            #
        #                                                                      #
        ########################################################################

        BatFiles = {}
        TotalNumberOfFiles = 0
        for satellite in SATELLITE:
            BatFiles[satellite] = {}
            for zone in ZONES[satellite]:
                BatFiles[satellite][zone] = CalcQualityFiles(satellite,zone)
                TotalNumberOfFiles = TotalNumberOfFiles + len(BatFiles[satellite][zone])

        if (TotalNumberOfFiles > 0):
            print TimeString(),'-> Step 5 - Creating Band Quality Images: Running',TotalNumberOfFiles,'Processes'
            LogOutput = open(LOG,'a')
            LogOutput.write(TimeString() + ' -> Step 5 - Creating Band Quality Images: Running ' + str(TotalNumberOfFiles) + ' Processes\n')
            LogOutput.close()

    ############################################################################
    #                                                                          #
    #  Check the log files for errors.                                         #
    #                                                                          #
    ############################################################################

    # If the HTML lines haven't changed, nothing has happened and, thus, there
    # is no need to check the .log files.
    if (HTML_Lines_Changed):
        FINALCHECK = True
        for satellite in SATELLITE:
            for zone in ZONES[satellite]:
                New_HTML_LINES = CheckLogFiles(satellite,COMPOSITEDIRECTORIES,zone + '*_quality.log',FINALCHECK)
            HTML_LINES[satellite].extend(New_HTML_LINES[satellite])

    ############################################################################
    #                                                                          #
    #  Clean up.  ERDAS 2013 leaves behind these query*.log files, which are   #
    #  meaningless and can be deleted.                                         #
    #                                                                          #
    ############################################################################

    QueryFiles = glob.glob('Query*.log')
    for File in QueryFiles:
        try:
            os.remove(File)
        except Exception, error:
            print error

    if (HTML_Lines_Changed):
        for satellite in SATELLITE:
            HTML_LINES[satellite].append("</ul>\n")
            HTML_LINES[satellite].append("</dl>\n")
        return HTML_LINES
    else:
        return {}


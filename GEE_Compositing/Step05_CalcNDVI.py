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
#  Calcuates NDVI.                                                             #
#                                                                              #
#  Used in the script MODIS_Daily_Processing.py                                #
#                                                                              #
################################################################################
#                                                                              #
#  IMPORT PYTHON MODULES                                                       #
#                                                                              #
################################################################################

import time, pp, os
import imagine

################################################################################
#                                                                              #
#  IMPORT CUSTOM PYTHON MODULES                                                #
#                                                                              #
#  AssignProcessesToCPUs: used to assign processes to individual processors    #
#  GetInputFilesForCompositeModels: used to get input and output filenames     #
#  TimeString: used to get and format the current time for printing purposes   #
#                                                                              #
################################################################################

from AssignProcessesToCPUs import GetFileDict
import GetInputFilesForCompositeModels
from TimeString import TimeString

################################################################################
#                                                                              #
#  VARIABLE DESCRIPTIONS                                                       #
#                                                                              #
#******************************************************************************#
#                                                                              #
#  SCRIPT DEFINED VARIABLES                                                    #
#                                                                              #
#  COMPOSITEDIRECTORIES: because composite periods overlap, each day, except   #
#                          for days 1-8, belong to two composite periods.      #
#                          COMPOSITEDIRECTORIES contains a list of composite   #
#                          directories for a particular day. For example, the  #
#                          compositing directoies for day 9 are:               #
#                          ['W:/TERRA/composites/2014/001_016','W:/TERRA/composites/2014/009_024']
#  PROCESSING_DIRECTORY: processing directories for each satellite             #
#                                                                              #
#******************************************************************************#
#                                                                              #
#  USER DEFINED VARIABLES                                                      #
#                                                                              #
#  NCPUS: number of CPUs available for processing                              #
#  SATELLITE: type of satellite sensor (i.e., AQUA, TERRA)                     #
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

NCPUS = int(os.environ['NUMBER_OF_PROCESSORS'])
SATELLITE = ['TERRA','AQUA']

COMPOSITEDIRECTORIES = {}
PROCESSING_DIRECTORY = {}

HTML_LINES = {}

LOG = 'W:/scripts/Logs/log_' + str(time.localtime()[7]) + '.txt'

################################################################################
#                                                                              #
#  Function: CalcMeanFocalSDFiles                                              #
#                                                                              #
#  Function Purpose:                                                           #
#                                                                              #
#  Calculate mean focal standard deviation.                                    #
#                                                                              #
################################################################################

def CalculateNDVI(InputImages):

    # TimesDict is used solely to print stuff to the HTML.
    TimesDict = {}
    
    for Image in InputImages:

        TimesDict[Image[2]] = {}
        TimesDict[Image[2]]['start'] = TimeString()
        TimesDict[Image[2]]['error'] = ''
        try:
            # Define the input and output images.
            InputFile = Image[0].replace('\\','/')
            MaskFile = Image[1].replace('\\','/')
            OutputFile = Image[2].replace('\\','/')

            # Set the background value.
            BackgroundValue = -1000

            # Create the ERDAS model.
            NDVIModel = imagine.modeler.Model()

            # Load the MODIS swath input image.
            InputImage = NDVIModel.RasterInput(InputFile, DataType = 'Float')

            # Load the mask input image.
            MaskInputImage = NDVIModel.RasterInput(MaskFile, DataType = 'Integer')

            # Define the bands.
            Layer1 = NDVIModel.BandSelection(InputImage,'1')
            Layer2 = NDVIModel.BandSelection(InputImage,'2')

            # Create some masks.
            Layer1Mask = NDVIModel.EitherOr(NDVIModel.Eq(Layer1,0),0,MaskInputImage)
            Layer2Mask = NDVIModel.EitherOr(NDVIModel.Eq(Layer2,0),0,MaskInputImage)

            # Calculate the NDVI.
            Band2MinusBand1 = NDVIModel.Subtract(Layer2,Layer1)
            Band2PlusBand1 = NDVIModel.Add(Layer1,Layer2)
            NDVI = NDVIModel.EitherOr(NDVIModel.Eq(Band2PlusBand1,0),BackgroundValue,NDVIModel.Divide(Band2MinusBand1,Band2PlusBand1))

            # If NDVI was 0, change it to -0.00001.
            NDVIAdjusted0 = NDVIModel.EitherOr(NDVIModel.Eq(NDVI,0),-0.00001,NDVI)

            # Mask the NDVI.
            NDVIMasked = NDVIModel.Multiply(NDVIAdjusted0,Layer2Mask,Layer1Mask,MaskInputImage)

            # Define the output image.
            OutputImage = NDVIModel.RasterOutput(NDVIMasked,OutputFile, PixelType = 'f32', Thematicity = 'Continuous',ComputePyramids = False)

            # Run the model.
            NDVIModel.Execute()
        except Exception, error:
            TimesDict[Image[2]]['error'] = 'error creating ' + Image[2] + '; ' + str(error)
        TimesDict[Image[2]]['end'] = TimeString()
    return TimesDict

################################################################################
#                                                                              #
#  Function: Run                                                               #
#                                                                              #
################################################################################

def Run(date):

    HTML_Lines_Changed = False

    ############################################################################
    #                                                                          #
    #  Get a list of input images for each satellite.                          #
    #                                                                          #
    ############################################################################

    InputFilesDict = {}
    InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE,PROCESSING_DIRECTORY,COMPOSITEDIRECTORIES,['_ndvi_01.img','_ndvi_01.ige'])
    NumberOfFiles = 0
    InputFilesList = []
    OutputImagesList = {}
    for satellite in InputFilesDict.keys():
        OutputImagesList[satellite] = []
        NumberOfFiles = NumberOfFiles + len(InputFilesDict[satellite])
        InputFilesList.extend(InputFilesDict[satellite])
        for Images in InputFilesDict[satellite]:
            OutputImagesList[satellite].append(Images[2])
    InputFilesList.sort()

    LogOutput = open(LOG,'a')
    count = 0
    while (NumberOfFiles != 0) & (count < 10):
        count = count + 1
        
        print TimeString(),'-> creating',NumberOfFiles,'NDVI images'
        LogOutput.write(TimeString() + ' -> creating ' + str(NumberOfFiles) + ' NDVI images\n')
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
                HTML_LINES[satellite].append("<p><b><span style='font-size:20.0pt'>Processing Day: " + satellite.upper() + " " + date + "</span></b></p>\n")

            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<dl>\n")
            HTML_LINES[satellite].append("<dt><b>Calculate NDVI</b></dt>\n")

            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<dd>" + TimeString() + " -> Processing " + str(len(InputFilesDict[satellite])) + " Files</dd>\n")
            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<ul>\n")

        ########################################################################
        #                                                                      #
        #  Assign processes to the CPUs                                        #
        #                                                                      #
        ########################################################################
            
        FileDict = GetFileDict(NCPUS,InputFilesList)

        ########################################################################
        #                                                                      #
        #  Run the process                                                     #
        #                                                                      #
        ########################################################################

        job_server = pp.Server()
        Results = [job_server.submit(CalculateNDVI,(FileDict[cpu],),(TimeString,),('imagine','time')) for cpu in range(1,NCPUS+1)]
        job_server.wait()
        job_server.print_stats()
        job_server.destroy()

        ########################################################################
        #                                                                      #
        #  Write stuff to HTML                                                 #
        #                                                                      #
        ########################################################################

        for Dict in Results:
            for Image in Dict().keys():
                for satellite in SATELLITE:
                    print 'Processing',Image,'Started:',Dict()[Image]['start'],'Ended:',Dict()[Image]['end']
                    LogOutput.write('Processing ' + Image + ' Started: ' + str(Dict()[Image]['start']) + ' Ended: ' + str(Dict()[Image]['end']) + '\n')
                    try:
                        x = OutputImagesList[satellite].index(Image)
                    except:
                        pass
                    else:
                        if (Dict()[Image]['error'] != ''):
                            HTML_LINES[satellite].append("<li><font color = 'red'>" + Dict()[Image]['error'] + "</font></li>\n")
                        else:
                            HTML_LINES[satellite].append("<li>Processing " + Image + " Started: " + Dict()[Image]['start'] + " Ended: " + Dict()[Image]['end'] + "</li>\n")

        ########################################################################
        #                                                                      #
        #  Get a list of input images for each satellite.                      #
        #                                                                      #
        ########################################################################

        InputFilesDict = {}
        InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE,PROCESSING_DIRECTORY,COMPOSITEDIRECTORIES,['_ndvi_01.img','_ndvi_01.ige'])
        NumberOfFiles = 0
        InputFilesList = []
        OutputImagesList = {}
        for satellite in InputFilesDict.keys():
            OutputImagesList[satellite] = []
            NumberOfFiles = NumberOfFiles + len(InputFilesDict[satellite])
            InputFilesList.extend(InputFilesDict[satellite])
            for Images in InputFilesDict[satellite]:
                OutputImagesList[satellite].append(Images[2])
        InputFilesList.sort()

    LogOutput.close()

    if (HTML_Lines_Changed):
        for satellite in SATELLITE:
            HTML_LINES[satellite].append("</ul>\n")
            HTML_LINES[satellite].append("</dl>\n")
        return HTML_LINES
    else:
        return {}


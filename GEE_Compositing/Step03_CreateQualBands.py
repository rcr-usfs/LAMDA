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
#  Creates quality images, which are rankings of the sums of bands 1,2,4.      #
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
from TimeString import TimeString
import GetInputFilesForCompositeModels

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
#  Function: CreateQualBands124Images                                          #
#                                                                              #
#  Function Purpose:                                                           #
#                                                                              #
#  Creates quality band images by adding bands 1,2,4 and ranking them.         #
#                                                                              #
################################################################################

def CreateQualBands124Images(InputImages):

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

            # Create the ERDAS model.
            QualBandsModel = imagine.modeler.Model()

            # Load the mask input image.
            MaskInputImage = QualBandsModel.RasterInput(MaskFile, DataType = 'Integer')

            # Load the MODIS swath input image.
            InputImage = QualBandsModel.RasterInput(InputFile, DataType = 'Integer')

            # Define the bands.
            Layer1 = QualBandsModel.BandSelection(InputImage,'1')
            Layer2 = QualBandsModel.BandSelection(InputImage,'2')
            Layer4 = QualBandsModel.BandSelection(InputImage,'4')

            # Add bands 1,2, and 4.
            Add124 = QualBandsModel.Add(Layer1,Layer2,Layer4)

            # Assign a quality ranking to the added bands.
            QualBands = QualBandsModel.Conditional(QualBandsModel.Lt(Add124,1000), QualBandsModel.Multiply(MaskInputImage,10), QualBandsModel.Lt(Add124,2000), QualBandsModel.Multiply(MaskInputImage,20), QualBandsModel.Lt(Add124,3000), QualBandsModel.Multiply(MaskInputImage,30), QualBandsModel.Lt(Add124,4000), QualBandsModel.Multiply(MaskInputImage,40), QualBandsModel.Lt(Add124,5000), QualBandsModel.Multiply(MaskInputImage,50), QualBandsModel.Lt(Add124,6000), QualBandsModel.Multiply(MaskInputImage,60), QualBandsModel.Lt(Add124,7000), QualBandsModel.Multiply(MaskInputImage,70), QualBandsModel.Lt(Add124,8000), QualBandsModel.Multiply(MaskInputImage,80), QualBandsModel.Lt(Add124,9000), QualBandsModel.Multiply(MaskInputImage,90), QualBandsModel.Ge(Add124,9000), QualBandsModel.Multiply(MaskInputImage,100))

            # Define the output image.
            OutputImage = QualBandsModel.RasterOutput(QualBands,OutputFile, PixelType = 'u8', Thematicity = 'Thematic',ComputePyramids = False)

            # Run the model.
            QualBandsModel.Execute()
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
    InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE, PROCESSING_DIRECTORY, COMPOSITEDIRECTORIES, ['_qual_bands124.img','_qual_bands124.ige'])
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

        print TimeString(),'-> creating',NumberOfFiles,'quality bands images'
        LogOutput.write(TimeString() + ' -> creating ' + str(NumberOfFiles) + ' quality bands images\n')
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
            HTML_LINES[satellite].append("<dt><b>Create Quality Band Images</b></dt>\n")

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
        Results = [job_server.submit(CreateQualBands124Images,(FileDict[cpu],),(TimeString,),('imagine','time')) for cpu in range(1,NCPUS+1)]
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
                    LogOutput.write('Processing ' + Image + ' Started: ' + str(Dict()[Image]['start']) + ' Ended: '+ str(Dict()[Image]['end']) + '\n')
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
        InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE, PROCESSING_DIRECTORY, COMPOSITEDIRECTORIES, ['_qual_bands124.img','_qual_bands124.ige'])
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


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
#  Calcuates mean focal standard deviation (sd).                               #
#                                                                              #
#  Used in the script MODIS_Daily_Processing.py                                #
#                                                                              #
################################################################################
#                                                                              #
#  IMPORT PYTHON MODULES                                                       #
#                                                                              #
################################################################################

import time, pp, os, subprocess, glob

################################################################################
#                                                                              #
#  IMPORT CUSTOM PYTHON MODULES                                                #
#                                                                              #
#  AssignProcessesToCPUs: used to assign processes to individual processors    #
#  CheckLogFiles: Checks .log files for errors                                 # 
#  CreateBatFiles: Used to create ERDAS formatted DOS bat files                #
#  GetInputFilesForCompositeModels: used to get input and output filenames     #
#  RunBatchFiles: used to run the .bat files                                   #
#  TimeString: used to get and format the current time for printing purposes   #
#                                                                              #
################################################################################

from AssignProcessesToCPUs import GetFileDict
from CheckLogFiles import CheckLogFiles
from CreateBatFiles import CreateBatFile
import GetInputFilesForCompositeModels
from RunBatchFiles import RunBatchFile
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
ERDAS_Executable = 'C:/Intergraph/ERDAS IMAGINE 2013/bin/Win32Release/eml.exe'

################################################################################
#                                                                              #
#  Function: CalculateMeanFocalSD                                              #
#                                                                              #
#  Function Purpose:                                                           #
#                                                                              #
#  Calculate mean focal standard deviation.                                    #
#                                                                              #
################################################################################

def CalculateMeanFocalSD():
    InputFiles = {}

    print TimeString(),'-> List of mean focal sd models'
    LogOutput = open(LOG,'a')
    LogOutput.write(TimeString() + ' -> List of mean focal sd models\n')

    InputFilesDict = {}
    InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE,PROCESSING_DIRECTORY,COMPOSITEDIRECTORIES,['_focal_sd_01.img','_focal_sd_01.ige'])
    for satellite in InputFilesDict.keys():
        InputFiles[satellite] = []
        for Inputs in InputFilesDict[satellite]:
            InputFile = Inputs[0]
            MaskFile = Inputs[1]
            OutputFile = Inputs[2]

            ModelText = []
            ModelText.append('SET CELLSIZE MIN;\n')
            ModelText.append('SET WINDOW INTERSECTION;\n')
            ModelText.append('SET AOI NONE;\n\n')

            ModelText.append('INTEGER RASTER InputImage FILE OLD PUBINPUT NEAREST NEIGHBOR AOI NONE "' + InputFile + '";\n')
            ModelText.append('INTEGER RASTER ImageMask FILE OLD PUBINPUT NEAREST NEIGHBOR AOI NONE "' + MaskFile + '";\n')
            ModelText.append('FLOAT RASTER OutputImage FILE NEW PUBOUT IGNORE 0 ATHEMATIC FLOAT SINGLE "' + OutputFile + '";\n')
            ModelText.append('INTEGER MATRIX Filter5x5;\n\n')

            ModelText.append('Filter5x5 = MATRIX(5, 5:\n')
            ModelText.append('	1, 1, 1, 1, 1, \n')
            ModelText.append('	1, 1, 1, 1, 1, \n')
            ModelText.append('	1, 1, 1, 1, 1, \n')
            ModelText.append('	1, 1, 1, 1, 1, \n')
            ModelText.append('	1, 1, 1, 1, 1);\n\n')

            ModelText.append('#define Mask FLOAT(EITHER 0.0 IF ( $InputImage(1) == 0 || $InputImage(2) == 0 || $InputImage(3) == 0 || $InputImage(4) == 0 || $InputImage(7) == 0 ) OR FLOAT($ImageMask) OTHERWISE )\n')
            ModelText.append('#define Band7_FocalSD FLOAT(FOCAL STANDARD DEVIATION ( $InputImage(7) , $Filter5x5 ) )\n')
            ModelText.append('#define Band4_FocalSD FLOAT(FOCAL STANDARD DEVIATION ( $InputImage(4) , $Filter5x5 ) )\n')
            ModelText.append('#define Band3_FocalSD FLOAT(FOCAL STANDARD DEVIATION ( $InputImage(3) , $Filter5x5 ) )\n')
            ModelText.append('#define Band2_FocalSD FLOAT(FOCAL STANDARD DEVIATION ( $InputImage(2) , $Filter5x5 ) )\n')
            ModelText.append('#define Band1_FocalSD FLOAT(FOCAL STANDARD DEVIATION ( $InputImage(1) , $Filter5x5 ) )\n')
            ModelText.append('#define FocalSD_Stack FLOAT(STACKLAYERS ( $Band1_FocalSD , $Band2_FocalSD , $Band3_FocalSD , $Band4_FocalSD , $Band7_FocalSD ))\n')
            ModelText.append('#define Mean_FocalSD FLOAT(STACK MEAN ( $FocalSD_Stack ) )\n')
            ModelText.append('OutputImage = EITHER  -1000.0 IF ( $Mean_FocalSD == 0.0 && $Mask == 1.0 ) OR $Mean_FocalSD * $Mask OTHERWISE ;\n')
            ModelText.append('QUIT;\n')
            InputFiles[satellite].append(CreateBatFile(COMPOSITEDIRECTORIES[satellite][0].replace('\\','/'), os.path.splitext(os.path.split(OutputFile)[1])[0],ModelText))
            print os.path.splitext(os.path.split(OutputFile)[1])[0] + '.mdl'
            LogOutput.write(os.path.splitext(os.path.split(OutputFile)[1])[0] + '.mdl\n')
    
    LogOutput.close()
    return InputFiles

##    # TimesDict is used solely to print stuff to the HTML.
##    TimesDict = {}
##    for Image in InputImages:
##
##        TimesDict[Image[2]] = {}
##        TimesDict[Image[2]]['start'] = TimeString()
##        TimesDict[Image[2]]['error'] = ''
##        try:
##
##            # Define the input and output images.
##            InputFile = Image[0].replace('\\','/')
##            MaskFile = Image[1].replace('\\','/')
##            OutputFile = Image[2].replace('\\','/')
##
##            # Create the ERDAS model.
##            MeanFocalSDModel = imagine.modeler.Model()
##
##            # Load the mask input image and the MODIS swath input image.
##            MaskInputImage = MeanFocalSDModel.RasterInput(MaskFile, DataType = 'Integer')
##            InputImage = MeanFocalSDModel.RasterInput(InputFile, DataType = 'Integer')
##
##            # Get the bands.
##            Layer1 = MeanFocalSDModel.BandSelection(InputImage,'1')
##            Layer2 = MeanFocalSDModel.BandSelection(InputImage,'2')
##            Layer3 = MeanFocalSDModel.BandSelection(InputImage,'3')
##            Layer4 = MeanFocalSDModel.BandSelection(InputImage,'4')
##            Layer7 = MeanFocalSDModel.BandSelection(InputImage,'7')
##
##            # Create masks for each band.
##            Layer1Mask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer1,0),0,MaskInputImage)
##            Layer2Mask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer2,0),0,MaskInputImage)
##            Layer3Mask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer3,0),0,MaskInputImage)
##            Layer4Mask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer4,0),0,MaskInputImage)
##            Layer7Mask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer7,0),0,MaskInputImage)
##
##            # Define the kernel that will be used to calculate the mean
##            # focal sd.
##            Matrix5x5 = MeanFocalSDModel.KernelMatrixInput(MatrixType = 'Integer', KernelLibrary = 'C:/Intergraph/ERDAS IMAGINE 2013/etc/default.klb', KernelName = '5x5 Low Pass', Normalize = False)
##
##            # Calculate the focal sd for each layer.
##            FocalSD_Layer1 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer1Mask,1),MeanFocalSDModel.FocalStandardDeviation(Layer1,Matrix5x5,IgnoreValue = 0.0),0)
##            FocalSD_Layer2 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer2Mask,1),MeanFocalSDModel.FocalStandardDeviation(Layer2,Matrix5x5,IgnoreValue = 0.0),0)
##            FocalSD_Layer3 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer3Mask,1),MeanFocalSDModel.FocalStandardDeviation(Layer3,Matrix5x5,IgnoreValue = 0.0),0)
##            FocalSD_Layer4 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer4Mask,1),MeanFocalSDModel.FocalStandardDeviation(Layer4,Matrix5x5,IgnoreValue = 0.0),0)
##            FocalSD_Layer7 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Layer7Mask,1),MeanFocalSDModel.FocalStandardDeviation(Layer7,Matrix5x5,IgnoreValue = 0.0),0)
##
##            # Calculate the mean focal sd.
##            Mean = MeanFocalSDModel.Mean(FocalSD_Layer1,FocalSD_Layer2,FocalSD_Layer3,FocalSD_Layer4,FocalSD_Layer7)
##
##            # Create some masks.
##            ZerosMask = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(Mean,0),1,0)
##            Mask = MeanFocalSDModel.Multiply(Layer1Mask,Layer2Mask,Layer3Mask,Layer4Mask,Layer7Mask,MaskInputImage)
##            RealZerosMask = MeanFocalSDModel.Multiply(ZerosMask,Mask)
##
##            # Mask the mean focal sd image.
##            Recode0 = MeanFocalSDModel.EitherOr(MeanFocalSDModel.Eq(RealZerosMask,1),-1000,Mean)
##            MaskedMean = MeanFocalSDModel.Multiply(Recode0,Mask)
##
##            # Define the output image.
##            OutputImage = MeanFocalSDModel.RasterOutput(MaskedMean,OutputFile, PixelType = 'f32', Thematicity = 'Continuous',ComputePyramids = False)
##
##            # Run the model.
##            MeanFocalSDModel.Execute()
##
##        except Exception, error:
##            TimesDict[Image[2]]['error'] = 'error creating ' + Image[2] + '; ' + str(error)
##        TimesDict[Image[2]]['end'] = TimeString()
##    return TimesDict

################################################################################
#                                                                              #
#  Function: Run                                                               #
#                                                                              #
################################################################################

def Run(date):
    global FINALCHECK

    FINALCHECK = False
    HTML_Lines_Changed = False

    ############################################################################
    #                                                                          #
    #  Get a list of input images for each satellite.                          #
    #                                                                          #
    ############################################################################

    BatFilesDict = CalculateMeanFocalSD()
    NumberOfFiles = 0
    BatFilesList = []
    for satellite in BatFilesDict.keys():
        NumberOfFiles = NumberOfFiles + len(BatFilesDict[satellite])
        BatFilesList.extend(BatFilesDict[satellite])
    BatFilesList.sort()
    
##
##    InputFilesDict = {}
##    InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE,PROCESSING_DIRECTORY,COMPOSITEDIRECTORIES,['_focal_sd_01.img','_focal_sd_01.ige'])
##    NumberOfFiles = 0
##    InputFilesList = []
##    OutputImagesList = {}
##    for satellite in InputFilesDict.keys():
##        OutputImagesList[satellite] = []
##        NumberOfFiles = NumberOfFiles + len(InputFilesDict[satellite])
##        InputFilesList.extend(InputFilesDict[satellite])
##        for Images in InputFilesDict[satellite]:
##            OutputImagesList[satellite].append(Images[2])
##    InputFilesList.sort()

    ############################################################################
    #                                                                          #
    #  Run the bat files.  The purpose of the while loop is sometimes ERDAS    #
    #  will not run a process for some unknown reason.  The loop will continue #
    #  to run until there are no files left to process or the loop has run 10  #
    #  times.                                                                  #
    #                                                                          #
    ############################################################################

    ERDASIsRunning = False
    if (len(BatFilesList) != 0):
        EML = subprocess.Popen(ERDAS_Executable, close_fds=True)
        time.sleep(60)
        ERDASIsRunning = True

    
    count = 0
    while (NumberOfFiles != 0) & (count < 10):
        count = count + 1

        print TimeString(),'-> creating',NumberOfFiles,'mean focal sd images'
        LogOutput = open(LOG,'a')
        LogOutput.write(TimeString() + ' -> creating ' + str(NumberOfFiles) + ' mean focal sd images\n')
        LogOutput.close()

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
            HTML_LINES[satellite].append("<dt><b>Mean Focal SD</b></dt>\n")

            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<dd>" + TimeString() + " -> Processing " + str(len(BatFilesDict[satellite])) + " Files</dd>\n")
            HTML_LINES[satellite].append("<p></p>\n")
            HTML_LINES[satellite].append("<ul>\n")

        ########################################################################
        #                                                                      #
        #  Assign processes to the CPUs                                        #
        #                                                                      #
        ########################################################################
            
        FileDict = GetFileDict(NCPUS,BatFilesList)

        ########################################################################
        #                                                                      #
        #  Run the process                                                     #
        #                                                                      #
        ########################################################################

        job_server = pp.Server()
        [job_server.submit(RunBatchFile, (FileDict[cpu],),(),('subprocess',)) for cpu in range(1,NCPUS+1)]
#        Results = [job_server.submit(CalculateMeanFocalSD,(FileDict[cpu],),(TimeString,),('imagine','time')) for cpu in range(1,NCPUS+1)]
        job_server.wait()
        job_server.print_stats()
        job_server.destroy()

        ########################################################################
        #                                                                      #
        #  Check the log files for errors.                                     #
        #                                                                      #
        ########################################################################

        Directories = {}
        for satellite in SATELLITE:
            Directories[satellite] = COMPOSITEDIRECTORIES[satellite][0]
            New_HTML_LINES = CheckLogFiles(satellite,Directories,'path*_noimage_mask.log',FINALCHECK)
            HTML_LINES[satellite].extend(New_HTML_LINES[satellite])

##        ########################################################################
##        #                                                                      #
##        #  Write stuff to HTML                                                 #
##        #                                                                      #
##        ########################################################################
##
##        for Dict in Results:
##            for Image in Dict().keys():
##                for satellite in SATELLITE:
##                    print 'Processing',Image,'Started:',Dict()[Image]['start'],'Ended:',Dict()[Image]['end']
##                    LogOutput.write('Processing ' + Image + ' Started: ' + str(Dict()[Image]['start']) + ' Ended: ' + str(Dict()[Image]['end']) + '\n')
##                    try:
##                        x = OutputImagesList[satellite].index(Image)
##                    except:
##                        pass
##                    else:
##                        if (Dict()[Image]['error'] != ''):
##                            HTML_LINES[satellite].append("<li><font color = 'red'>" + Dict()[Image]['error'] + "</font></li>\n")
##                        else:
##                            HTML_LINES[satellite].append("<li>Processing " + Image + " Started: " + Dict()[Image]['start'] + " Ended: " + Dict()[Image]['end'] + "</li>\n")
##
        ########################################################################
        #                                                                      #
        #  Get a list of input images for each satellite.                      #
        #                                                                      #
        ########################################################################

        BatFilesDict = CalculateMeanFocalSD()
        NumberOfFiles = 0
        BatFilesList = []
        for satellite in BatFilesDict.keys():
            NumberOfFiles = NumberOfFiles + len(BatFilesDict[satellite])
            BatFilesList.extend(BatFilesDict[satellite])
        BatFilesList.sort()

##        InputFilesDict = {}
##        InputFilesDict = GetInputFilesForCompositeModels.GetInputImages(SATELLITE,PROCESSING_DIRECTORY,COMPOSITEDIRECTORIES,['_focal_sd_01.img','_focal_sd_01.ige'])
##        NumberOfFiles = 0
##        InputFilesList = []
##        OutputImagesList = {}
##        for satellite in InputFilesDict.keys():
##            OutputImagesList[satellite] = []
##            NumberOfFiles = NumberOfFiles + len(InputFilesDict[satellite])
##            InputFilesList.extend(InputFilesDict[satellite])
##            for Images in InputFilesDict[satellite]:
##                OutputImagesList[satellite].append(Images[2])
##        InputFilesList.sort()

    if (ERDASIsRunning):
        KillERDAS = subprocess.Popen('tskill eml* /a', close_fds=True)

    ############################################################################
    #                                                                          #
    #  Check the log files for errors.                                         #
    #                                                                          #
    ############################################################################

    # If the HTML lines haven't changed, nothing has happened and, thus, there
    # is no need to check the .log files.
    if (HTML_Lines_Changed):
        FINALCHECK = True
        Directories = {}
        for satellite in SATELLITE:
            Directories[satellite] = COMPOSITEDIRECTORIES[satellite][0]
            New_HTML_LINES = CheckLogFiles(satellite,Directories,'path*_noimage_mask.log',FINALCHECK)
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

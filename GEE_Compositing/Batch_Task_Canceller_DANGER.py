

#Script to cancel all running tasks for a provided set of credentials

#Code written by: Ian Housman
#Original code written by: Robert Chastain

#Module imports
import exportManager
from multiprocessing import Pool,Process
import multiprocessing,sys,time,os,urllib,threading,subprocess,time,datetime


from geeViz.getImagesLib import *
#########################################################################
def cancelTasks(i):
    credentials = exportManager.GetPersistentCredentials(exportManager.credentials[i])
    credentialsName = os.path.basename(exportManager.credentials[i])
    exportManager.ee.Initialize(credentials)
    tasks = ee.data.getTaskList()
    cancelledTasks = []
    for ind, i in enumerate(tasks):
        if (i['state'] == 'READY' or i['state'] == 'RUNNING') and i['description'].find('PY_TDD_Baseline_Medoid_cloudScore_TDOM')>-1:
            print('Cancelling:',i['description'])
            ee.data.cancelTask(i['id'])
def batchCancelTasks():
    for i in range(exportManager.nCredentials):
        print(i)   
        p = Process(target = cancelTasks,args = (i,),name = str(i))
        p.start()
        time.sleep(0.2)

if __name__ == '__main__':  
    batchCancelTasks()

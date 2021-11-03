#! /usr/bin/python

#
# Description: This package will perform many tasks required for l-t separation physics analysis 
# Analysis script required format for applying cuts...
'''
import uproot as up
sys.path.insert(0, 'path_to/bin/python/')
import kaonlt as klt

# Convert root leaf to array with uproot
# Array name must match what is defined in DB/CUTS/general/
array  = tree.array("leaf")

# Not required for applying cuts, but required for converting back to root files
r = klt.pyRoot()

fout = "<path_to_run_type_cut>"

cuts = ["<list of cuts>"]

cutVals = []
def make_cutDict(cuts,fout,runNum,CURRENT_ENV):
    ''
    This method calls several methods in kaonlt package. It is required to create properly formated
    dictionaries. The evaluation must be in the analysis script because the analysis variables (i.e. the
    leaves of interest) are not defined in the kaonlt package. This makes the system more flexible
    overall, but a bit more cumbersome in the analysis script. Perhaps one day a better solution will be
    implimented.
    ''

    # read in cuts file and make dictionary
    importDict = lt.SetCuts(CURRENT_ENV).importDict(cuts,fout,runNum)
    for i,cut in enumerate(cuts):
        x = lt.SetCuts(CURRENT_ENV,importDict).booleanDict(cut)
        #######################################################################################
        # Make list of cut strings
        cutVals.append(x)

        # Threshold current
        if cut == "c_curr":
            global thres_curr, report_current
            # e.g. Grabbing threshold current (ie 2.5) from something like this [' {"H_bcm_bcm4a_AvgCurrent" : (abs(H_bcm_bcm4a_AvgCurrent-55) < 2.5)}']
            thres_curr = float(x[0].split(":")[1].split("<")[1].split(")")[0].strip())
            # e.g. Grabbing set current for run (ie 55) from something like this [' {"H_bcm_bcm4a_AvgCurrent" : (abs(H_bcm_bcm4a_AvgCurrent-55) < 2.5)}']
            report_current = float(x[0].split(":")[1].split("<")[0].split(")")[0].split("-")[1].strip())
        #######################################################################################
        print("\n%s" % cut)
        print(x, "\n")
        if i == 0:
            inputDict = {}
        cutDict = lt.SetCuts(CURRENT_ENV,importDict).readDict(cut,inputDict)
        for j,val in enumerate(x):
            cutDict = lt.SetCuts(CURRENT_ENV,importDict).evalDict(cut,eval(x[j]),cutDict)
    return lt.SetCuts(CURRENT_ENV,cutDict)

c = make_cutDict(cuts,fout,runNum,os.path.realpath(__file__))

# ---> If multple run type files are required then define a new run type file altogether. Do not try to 
# chain run type files. It can be done, but is computationally wasteful and pointless.

# To apply cuts to array...
c.add_cut(array,"cut#")

'''
# ================================================================
# Time-stamp: "2020-05-02 15:00:37 trottar"
# ================================================================
#
# Author:  Richard L. Trotta III <trotta@cua.edu>
#
# Copyright (c) trottar
#
import pandas as pd
import numpy as np
import os

# Import the pathing class of the module. This allows the database chosen based off your current directory. Allows for easier switching between pion and kaon.
from .pathing import SetPath

class SetCuts():
    '''
    This is the most extensive class of the kaonlt package. This class will perform many required tasks
    for doing in depth analysis in python. This class does not require, but will use the pyDict class to
    apply cuts. Set the dictionary to None if no cuts are required.
    '''

    def __init__(self, CURRENT_ENV,cutDict=None):
        self.cutDict = cutDict
        self.REPLAYPATH = SetPath(CURRENT_ENV).getPath("REPLAYPATH")
        self.UTILPATH = SetPath(CURRENT_ENV).getPath("UTILPATH")

    def setbin(self,plot,numbin,xmin=None,xmax=None):
        '''
        A method for defining a bin. This may be called in any matplotlib package plots.
        This will calculate a suitable bin width and use that to equally distribute the bin size
        '''
        
        if (xmin or xmax):
            leaf = self.fixBin(plot,plot,xmin,xmax)
        else:
            leaf = plot
            
        binwidth = (abs(leaf).max()-abs(leaf).min())/numbin
        
        bins = np.arange(min(leaf), max(leaf) + binwidth, binwidth)

        return bins

    def fixBin(self,cut,plot,low,high):
        '''
        This method is complimentary to setbin(). This will cut the distribution based off the min and max array values

        '''
        arrCut = cut
        arrPlot = plot
        arrPlot = arrPlot[(arrCut > low) & (arrCut < high)]

        return arrPlot

    def cut_RF(self,runNum,MaxEvent):
        TimingCutFile = self.UTILPATH+'/DB/PARAM/Timing_Parameters.csv'
        # rootName = "/lustre19/expphy/volatile/hallc/c-kaonlt/sjdkay/ROOTfiles/Proton_Analysis/Pass3/Proton_coin_replay_production_%s_%s.root" % (self.REPLAYPATH, runNum, MaxEvent)
        rootName = self.UTILPATH+"/ROOTfiles/coin_replay_Full_Lumi_%s_%s.root" % (runNum,MaxEvent)
        e_tree = up.open(rootName)["T"]
        TimingCutf = open(TimingCutFile)
        PromptPeak = [0, 0, 0]
        linenum = 0 # Count line number we're on
        TempPar = -1 # To check later
        for line in TimingCutf: # Read all lines in the cut file
            linenum += 1 # Add one to line number at start of loop
            if(linenum > 1): # Skip first line
                line = line.partition('#')[0] # Treat anything after a # as a comment and ignore it
                line = line.rstrip()
                array = line.split(",") # Convert line into an array, anything after a comma is a new entry
                if(int(runNum) in range (int(array[0]), int(array[1])+1)): # Check if run number for file is within any of the ranges specified in the cut file
                    TempPar += 2 # If run number is in range, set to non -1 value
                    BunchSpacing = float(array[2]) # Bunch spacing in ns
                    RF_Offset = float(array[9]) # Offset for RF timing cut
        TimingCutf.close() # After scanning all lines in file, close file
        if(TempPar == -1): # If value is still -1, run number provided didn't match any ranges specified so exit
            print("!!!!! ERROR !!!!!\n Run number specified does not fall within a set of runs for which cuts are defined in %s\n!!!!! ERROR !!!!!" % TimingCutFile)
            sys.exit(3)
        elif(TempPar > 1):
            print("!!! WARNING!!! Run number was found within the range of two (or more) line entries of %s !!! WARNING !!!" % TimingCutFile)
            print("The last matching entry will be treated as the input, you should ensure this is what you want")
        P_RF_tdcTime = e_tree.array("T.coin.pRF_tdcTime")
        P_hod_fpHitsTime = e_tree.array("P.hod.fpHitsTime")
        RF_CutDist = np.array([ ((RFTime-StartTime + RF_Offset)%(BunchSpacing)) for (RFTime, StartTime) in zip(P_RF_tdcTime, P_hod_fpHitsTime)]) # In python x % y is taking the modulo y of x

    def readDict(self,cut,inputDict=None):
        for key,val in self.cutDict.items():
            if key == cut:
                inputDict.update({key : {}})
        return inputDict

    def evalDict(self,cut,eval_xi,inputDict):
        inputDict[cut].update(eval_xi)
        return inputDict

    def importDict(self,inp_cuts,fout,runNum,DEBUG=False):
        '''
        This method imports in the CUTS and converts them to a dictionary. 
        '''

        # Open run type cuts of interest
        f = open(fout)
        cutDict = {}

        # Matches run type cuts with the general cuts (e.g pid, track, etc.)
        gencutDict = {
            "pid" : self.UTILPATH+"/DB/CUTS/general/pid.cuts",
            "track" : self.UTILPATH+"/DB/CUTS/general/track.cuts",
            "accept" : self.UTILPATH+"/DB/CUTS/general/accept.cuts",
            "coin_time" : self.UTILPATH+"/DB/CUTS/general/coin_time.cuts",
            "current" : self.UTILPATH+"/DB/CUTS/general/current.cuts",
            "misc" : self.UTILPATH+"/DB/CUTS/general/misc.cuts",
        }

        def genCut(cut_list,add_flag=True):
            '''
            Function to get the general cuts and calls the search_DB method to get the param values for each cut
            '''
            gencut = []
            # Loop over cut arguments
            for i,val in enumerate(cut_list):
                cutgen = val.split(".")
                if (DEBUG):
                    print("cutgen ", cutgen)
                # Get the general cut name 
                gencut.append(cutgen)
                if cutgen[0].strip() not in gencutDict:
                    print("!!!!ERROR!!!!: Added cut {0} not defined in {1}/DB/CUTS/general/".format(cutgen[0],self.UTILPATH)) # ERROR 2
                    print("Cut must be pid, track, accept, coin_time or current")
            if (DEBUG):
                print("gencuts ", gencut)
            for i,val in enumerate(gencut):
                # Open general cuts file of interest to be added to dictionary
                f = open(gencutDict[val[0]])
                for cutline in f:
                    # Ignore comments
                    if "#" in cutline:
                        continue
                    else:
                        # Redefine cut as 2nd element of list split at = (but only the first instance of =)
                        # This 2nd element are the general cuts
                        cutName = cutline.split("=",1)[0].strip().strip("\n")
                        cuts = cutline.split("=",1)[1].strip().strip("\n")
                        if add_flag:
                            # Check for general cut that was called
                            if val[1] == cutName:
                                # Check if run type is already defined in dictionary
                                if typName in cutDict.keys():
                                    if cuts not in cutDict.items():
                                        # If run type already defined, then append dictionary key
                                        if (DEBUG):
                                            print("cuts ",cuts)
                                            print("val ",val)
                                        # Grabs parameters from DB (see below)
                                        db_cut = self.search_DB(cuts,runNum,DEBUG)
                                        if (DEBUG):
                                            print(typName, " already found!!!!")
                                        cutDict[typName] += ","+db_cut
                                else:
                                    # If run type not defined, then add key to dictionary
                                    if (DEBUG):
                                        print("cuts ",cuts)
                                        print("val ",val)
                                    # Grabs parameters from DB (see below)
                                    db_cut = self.search_DB(cuts,runNum,DEBUG)
                                    cutName = {typName : db_cut}
                                    cutDict.update(cutName)
                            else:
                                continue
                        else:
                            # Break down the cut to be removed to find specific leaf to be subtracted from
                            # dictionary
                            #minuscut = gencut[0]
                            minuscut = val
                            if len(minuscut) == 3:
                                cutminus = minuscut[1]
                                leafminus = minuscut[2].rstrip()
                            elif minuscut == ['none']:
                                cutminus = "none"
                            else:
                                print("!!!!ERROR!!!!: Invalid syntax for removing cut %s " % (minuscut)) # Error 4
                                continue
                            # Split cuts to check for the one to be removed.
                            arr_cuts = cuts.split(",")
                            # Check for general cut that was called
                            if val[1] == cutName:
                                for remove in arr_cuts:
                                    # Check which cut matches the one wanted to be removed
                                    if leafminus in remove:
                                        # Grabs parameters from DB (see below)
                                        remove = self.search_DB(remove,runNum,DEBUG)
                                        if (DEBUG):
                                            print("Removing... ",remove)
                                        # Replace unwanted cut with blank string
                                        cutDict[typName] = cutDict[typName].replace(remove,"")
                f.close()
            return gencut


        def flatten(minus_list):
            flat_list = []
            for e in minus_list:
                if type(e) is list:
                    for i in e:
                        flat_list.append(i)
                else:
                    flat_list.append(e)
            return flat_list

        for ic in inp_cuts:
            if (DEBUG):
                print("\nInput ", ic)
            f.seek(0)
            for line in f:
                # Ignore comments
                if "#" in line:
                    continue
                else:
                    line = line.split("=",1)
                    # Grab run type cut name
                    typName = line[0].strip()
                    if ic == typName:
                        # Grab run type cuts required, note at this stage the cuts to be removed are bunched
                        # together still
                        pluscut = line[1].split("+")
                        pluscut = [i.strip().strip("\n") for i in pluscut]
                        if (DEBUG):
                            print("Type ", typName)
                            print("Cuts ", pluscut)
                        minuscut = [None]*len(pluscut)
                        # Loop over run type cuts being split by +
                        for i,evt in enumerate(pluscut):
                            # Split any cuts to be removed
                            cutminus = evt.split("-")
                            if len(cutminus) > 1:
                                # Define first cut to be added, any other cuts to be added will be done in future
                                # iteration over run type cuts
                                pluscut[i] = cutminus[0].strip()
                                # Ignore first element, since it will always be an added cut
                                minuscut[i] = cutminus[1:]
                        minuscut = flatten([x for x in minuscut if x is not None])
                        if (DEBUG):
                            print("+ ", pluscut)
                            print("- ", minuscut)
                        
                        ##############
                        # Added cuts #
                        ##############
                        if (DEBUG):
                            print("Cuts added...")
                        genpluscut = genCut(pluscut)

                        ###################
                        # Subtracted cuts #
                        ###################
                        if (DEBUG):
                            print("Cuts subtracted...")                
                        genminuscut = genCut(minuscut,add_flag=False)
                        break
        f.close()
        if (DEBUG):
            print("\n\n")
            print(cutDict.keys())
            print("\n\n")
        return cutDict

    def search_DB(self,cuts,runNum,DEBUG):
        '''
        Grabs the cut parameters from the database. In essence this method simply replaces one string with another
        '''
        # Split all cuts into a list
        cuts = cuts.split(",")
        db_cuts = []
        
        paramDict = {
            "accept" : self.UTILPATH+"/DB/PARAM/Acceptance_Parameters.csv",
            "track" : self.UTILPATH+"/DB/PARAM/Tracking_Parameters.csv",
            "CT" : self.UTILPATH+"/DB/PARAM/Timing_Parameters.csv",
            "pid" : self.UTILPATH+"/DB/PARAM/PID_Parameters.csv",
            "misc" : self.UTILPATH+"/DB/PARAM/Misc_Parameters.csv",
            "current" : self.UTILPATH+"/DB/PARAM/Current_Parameters.csv"
        }

        def grabCutData(paramName,cut):
            # Find which cut is being called
            if paramName in cut:
                paramVal = cut.split(paramName)
                for val in paramVal:
                    if "." in val and "abs" not in val:
                        paramVal = val.split(")")[0]
                        paramVal = paramVal.split(".")[1]
                        fout = paramDict[paramName]
                        try:
                            data = dict(pd.read_csv(fout))
                        except IOError:
                            print("ERROR 9: %s not found in %s" % (paramVal,fout))
                        for i,evt in enumerate(data['Run_Start']):
                            if data['Run_Start'][i] <= np.int64(runNum) <= data['Run_End'][i]:
                                cut  = cut.replace(paramName+"."+paramVal,str(data[paramVal][i]))
                                if (DEBUG):
                                    print("paramVal ",paramVal, "= ",data[paramVal][i])
                                pass
                            else:
                                # print("!!!!ERROR!!!!: Run %s not found in range %s-%s" % (np.int64(runNum),data['Run_Start'][i],data['Run_End'][i])) # Error 10
                                continue
                    else:
                        continue
            if paramName == "num":
                cut = cut
            db_cuts.append(cut.strip())

        # Returns true if number is in string
        def has_numbers(inputString):
            return any(char.isdigit() for char in inputString)
            
        for cut in cuts:
            # Find which cut is being called
            if "accept" in cut:
                grabCutData("accept",cut)
            elif "track" in cut:
                grabCutData("track",cut)
            elif "CT" in cut:
                grabCutData("CT",cut)
            elif "pid" in cut:
                grabCutData("pid",cut)
            elif "misc" in cut:
                grabCutData("misc",cut)          
            elif "current" in cut:
                grabCutData("current",cut)
            elif has_numbers(cut):
                grabCutData("num",cut)
            else:
                # print("ERROR 11: %s not defined" % cut)
                continue
            
        # Rejoins list of cuts to a string separated by commas
        db_cuts  = ','.join(db_cuts)
        return db_cuts

    def booleanDict(self,cuts):
        '''
        Create a boolean dictionary for cuts by converting string to array of pass/no pass cuts.
        '''

        inputDict = self.cutDict
        subDict = inputDict[cuts]
        subDict = subDict.split(",")
        cut_arr = [evt for evt in subDict]
        cut_arr = list(filter(None,cut_arr))
        return cut_arr

    def add_cut(self,arr, cuts):
        '''
        Applies cuts. The general idea is to apply cuts without sacrificing computation
        time. Array indexing is much faster than most methods in python. This method formats a string with
        the cuts required. This string is evaluated and the array index calls the cut() method.See
        description above for how the analysis script should be formatted. 
        '''

        arr_cut = arr  
        applycut = "arr_cut["
        inputDict = self.cutDict
        subDict = inputDict[cuts]
        for i,(key,val) in enumerate(subDict.items()):
            if i == len(subDict)-1:
                applycut += 'self.cut("%s","%s")]' % (key,cuts)
            else:
                applycut += 'self.cut("%s","%s") & ' % (key,cuts)
        arr_cut = eval(applycut)        
        return arr_cut

    def cut(self,key,cuts=None):
        '''
        The array index that was evaluated in the add_cut() method calls this method. This method then
        grabs the properly formated dictionary (from class pyDict) and outputs arrays with cuts.
        '''

        if cuts:
            inputDict = self.cutDict
            subDict = inputDict[cuts]
            value = subDict.get(key,"Leaf name not found")
            return value
        # Just for old version for applying cuts (i.e. applyCuts() method)
        else:
            return self.cutDict.get(key,"Leaf name not found")

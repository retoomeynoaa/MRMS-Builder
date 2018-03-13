#!/usr/bin/env python

# Robert Toomey March 2017
# Attempt to streamline the building process
# into something easier and braindead.

# System imports
import getpass,datetime,os
import sys,re
from subprocess import Popen, PIPE
from os.path import expanduser

# Relative imports (should work on 2 and 3)
from . import buildtools as b
from . import config as config

# Import the main group builders from all modules
# You'd add a module here if needed
from .ThirdParty import ThirdPartyBuild
from .MRMSSevere import MRMSSevereBuild
from .MRMSSevere import autoGUICheck as autoGUICheck
from .MRMSSevere import autoPythonDevCheck as autoPythonDevCheck
from .MRMSHydro import MRMSHydroBuild
from .WG2 import WG2Build
from .WG2 import autoGUI2Check as autoGUI2Check

red = "\033[1;31m"
blue = "\033[1;34m"
green = "\033[1;32m"
coff = "\033[0m"

MAJOR_VERSION = 1
MINOR_VERSION = 1

line = "------------------------------------------------"

def getTargetPaths():
  """ Return list of default paths for install """
  # Get Timestamp
  today = datetime.date.today()
  date = today.strftime("%Y%m%d")

  # Relative to script location (option 1)
  relativePath = os.path.dirname(os.path.realpath(__file__))
  oldpwd = os.getcwd()
  os.chdir(relativePath)
  os.chdir("..")
  os.chdir("..")
  relativePath = os.getcwd()
  os.chdir(oldpwd)

  # Paths
  relativePath = relativePath+"/MRMS"
  relativePathDate = relativePath+"_"+date
  homePath = expanduser("~")+"/"+"MRMS"
  homePathDate = homePath+"_"+date

  return[homePathDate, homePath, relativePathDate, relativePath]
  
def validatePath(aPath):
  """ Return true if path writable/changable """
  good = True
  # Try to create directory...
  if not os.path.exists(aPath):
    try:
      os.makedirs(aPath)
    except:
      print("I couldn't create directory "+aPath)
      good = False

  # Try to access directory...
  if not os.access(aPath, os.W_OK):
    print("...but I can't _access_ "+aPath+". Permission settings?")
    good = False

  return good

def getBuildFolder():
  """ Get the build folder """
  global theConf
  o = theConf.getString("TARGET", "", "")
  if o != "":
    theConf.addHistory("TARGET", "Target location", o)
    return o  

  [homePathDate, homePath, relativePathDate, relativePath] = getTargetPaths()

  myPrompts = [
               "Use Home Dated: " + green+homePathDate+coff,
               "Use Home: " + green+homePath+coff,
               "Use Relative Dated: " + green+relativePathDate+coff,
               "Use Relative: " + green+relativePath+coff,
              ]
  myOptions = ["1", "2", "3", "4"]
  mainPrompt = red+"Where"+coff+" would you like the build placed? (You can type a path as well)"
            
  while True:
    good = True

    o = b.pickOption1(mainPrompt, myPrompts, myOptions, "1", False, True)
    print("You choose: " +o)

    # Get the path wanted
    wanted = o 

    if (wanted == ""): # Use default of 1
      wanted = "1"

    if (wanted == "1"):
      wanted = homePathDate
    elif (wanted == "2"):
      wanted = homePath
    elif (wanted == "3"):
      wanted = relativePathDate
    elif (wanted == "4"):
      wanted = relativePath

    good = validatePath(wanted)

    if good:
      theConf.addHistory("TARGET", "Target location", wanted)
      return wanted

def addBuilder(aList, aBuilder, aBuildItFlag):
  """ Convenience function for adding builder """
  aBuilder.setBuild(aBuildItFlag)
  aList.append(aBuilder)
  return aBuilder

def buildMRMS():
  """ Build MRMS by checking out SVN with questions """
  global theConf

  # Try to use default cfg or one passed by user
  configFile = "default.cfg"
  if len(sys.argv) > 1:
    configFile = sys.argv[1]
  theConf = config.Configuration()
  confResult = theConf.readConfig(configFile)

  # Basic fall back user name/SVN settings
  user = getpass.getuser()
  b.setupSVN(user, False)

  print(line)
  #print("Welcome to the "+green+"MRMS project builder V1.0"+coff)
  version = str(MAJOR_VERSION)+"."+str(MINOR_VERSION)
  print("Welcome to the "+green+"MRMS project builder V"+version+coff)
  print("Using config file: "+configFile+" "+red+confResult+coff)
  print(line)
  print("Hi, "+blue+user+coff+", I'm your hopefully helpful builder.")
  print("Modify default.cfg and/or answer questions below:")

  #wantAdvanced = theConf.getBoolean("ADVANCED", "Do you want to see advanced options and tools?", "no")
  checkout = True
  checkout = theConf.getBoolean("CHECKOUT", "Checkout all code from SVN repository?", "yes")
  buildThird = theConf.getBoolean("THIRDPARTY", "Build all third party packages?", "yes")
  buildWDSS2 = theConf.getBoolean("WDSS2", "Build WDSS2 packages?", "yes")
  buildHydro = theConf.getBoolean("HYDRO", "Build Hydro packages after WDSS2?", "yes")
  buildGUI = theConf.getBooleanAuto("GUI", "Build the WG display gui? (requires openGL libraries installed)", "yes", autoGUICheck)
  buildGUI2 = theConf.getBooleanAuto("GUI2", "Build the WG2 java display gui? (requires ant 1.9 and java)", "yes", autoGUI2Check)

  isResearch = False
  isExport = False
  buildPython = False
  if (buildWDSS2):  # These flags only matter for WDSS2 part (for now at least)
    isResearch = theConf.getBoolean("RESEARCH", "Is this a research build (no realtime, no encryption)", "no")
    buildPython = theConf.getBooleanAuto("PYTHONDEV", "Build WDSS2 python development support?", "no", autoPythonDevCheck)
    if (isResearch):
      isExport = True # Research version automatically loses encryption
    else:
      isExport = theConf.getBoolean("EXPORT", "Is this an exported build (For outside US, turn off encryption)", "no")

  # Builder group packages, add in dependency order
  # To add a new module, add an 'from' import at top and add a line here
  bl = []
  thirdparty = addBuilder(bl, ThirdPartyBuild(), buildThird)
  mrmssevere = addBuilder(bl, MRMSSevereBuild(), buildWDSS2)
  mrmssevere.setWantGUI(buildGUI)
  mrmshydro = addBuilder(bl, MRMSHydroBuild(), buildHydro)
  # Only add the wg2builder if the user has requested to build WG2
  if buildGUI2:
    wg2builder = addBuilder(bl, WG2Build(), buildGUI2)

  ###################################################
  # Try to do stuff that could 'break' if misconfigured here before checking out...
  # Get all the "-D" cppflag options Lak spammed us with (see below)
  if buildWDSS2 == True:
    ourDFlags = theConf.getOurDFlags()
    if buildPython:
      ourDFlags["PYTHON_DEVEL"] = "2.7"
    if isExport:
      ourDFlags["EXPORT_VERSION"] = "" 
    #print("DEBUG:Ok OUR cppflags are:"+str(ourDFlags))
    #print("Expire flags: '"+expireFlags+"'")
    #  $ENV{CXXFLAGS} = "$required_flags $optimized $debug $sunrise $sunset $export_flags ${key_flags} $param{cxxflags}";

  # Get make flags here early in case it dies
  cpus = theConf.getJobs() 
  makeFlags = "--jobs="+cpus   # extra make flags

  # Check requirements for each wanted module
  #print ("Checking requirements for build...\n")
  req = True
  for bg in bl:
     if bg.getBuild():  # Only check if we're building it?
       req = req & bg.checkRequirements()
  if req == False:
    print("Missing installed libraries or rpms to build, contact IT to install.")
    sys.exit(1)
  ###################################################

  # Folder wanted.  Currently asked for...but could have 'smart' option
  folder = getBuildFolder()

  # User/password for SVN and checkout
  if checkout:
    #user = getUserName() user = getpass.getuser()
    uprompt ="What "+red+"username"+coff+" for SVN? (Use . for anonymous checkout if you aren't going to commit code.)"
    user = theConf.getString("USERNAME", uprompt, getpass.getuser())
    b.setupSVN(user, False) # Change user now
    if user == ".":
      password = "" # anonymous shouldn't ask for password
    else:
      passPrompt = "To checkout I might need your "+green+"NSSL"+coff+" password (I'll keep it secret)"
      password = theConf.getPassword("PASSWORD", passPrompt, user)
    revision = theConf.getString("REVISION", "What SVN --revision so you want?", "HEAD")
    revision = "-r "+revision
    print(blue+"Checking out code..."+coff)
    for bg in bl:
      bg.checkout(folder, password, revision)
    print(blue+"Check out success."+coff)

  w2cppflags = ""
  if buildWDSS2 == True:
    # Basically we use any -D values from Lak's auth files, overridden
    # by anything we express in our configure...and all these go to 
    # cppflags on make command line... 
    keypath = mrmssevere.getKeyLocation(folder, isResearch)
    authFileDFlags = theConf.getAuthFileDItems(keypath)
    map1 = theConf.mergeConfigLists(ourDFlags, authFileDFlags) # 2nd overrides...
    w2cppflags = theConf.listToDFlags(map1)
    mrmssevere.setCPPFlags(w2cppflags)

  # Build everything wanted (order matters here)
  for bg in bl:
     if bg.getBuild():
       # All using same make flags for now at least
       bg.setMakeFlags(makeFlags)
       bg.build(folder)

  # Calculate stuff for version 
  dateraw = datetime.datetime.now();
  mydate = dateraw.strftime("%Y-%m-%d-%H-%M-%S-%f")
  machine = os.uname()
  redhat = b.getFirst(["cat","/etc/redhat-release"])
  envuser = getpass.getuser()

  # Dump VERSION file to bin
  good = validatePath(folder+"/bin/") # make sure directory exists.
  if good:
    aFile = open(folder+"/bin/VERSION", "w")
    aFile.write("MRMS built using the MRMS_builder python scripts.\n")
    aFile.write("\tDate completed: "+mydate+"\n")
    aFile.write("\tRun by user: "+envuser+"\n")
    aFile.write("\tRun on machine:\n\t  ")
    for x in machine:
      aFile.write(x+" ")
    aFile.write("\n")
    aFile.write("\tRedhat info:\n\t  "+redhat+"\n")
    aFile.write("Options:\n")
    theConf.printFileHistory(aFile)
    aFile.close()
    good = validatePath(folder+"/lib/") # make sure directory exists.
    if good:
      b.runOptional("cp "+folder+"/bin/VERSION "+folder+"/lib/VERSION")

  theConf.printHistory()
  b.setupSVN(user, True)

if __name__ == "__main__":
  print("Run the ./build.py script to execute")

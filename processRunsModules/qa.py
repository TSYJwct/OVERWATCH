""" Contains all of the machinery to allow for basic QA.

.. codeauthor:: Raymond Ehlers <raymond.ehlers@cern.ch>, Yale University
"""

# Python 2/3 support
from __future__ import print_function

# General includes
import os
import sys

# Used to load functions from other modules
import importlib
import inspect

# Configuration
from config.processingParams import processingParameters

# Get the current module
# Used to load functions from other moudles and then look them up.
currentModule = sys.modules[__name__]

###################################################
class qaFunctionContainer(object):
    """ QA Container class

    Args:
        firstRun (str): The first (ie: lowest) run in the form "Run#". Ex: "Run123"
        lastRun (str): The last (ie: highest) run in the form "Run#". Ex: "Run123"
        runDirs (list): List of runs in the range [firstRun, lastRun], with entries in the form of "Run#" (str).
        qaFunctionName (str): Name of the QA function to be executed.

    Available attributes include:

    Attributes:
        currentRun (str): The current run being processed in the form "Run#". Ex: "Run123"
        hists (dict): Contains histograms with keys equal to the histogram label (often the hist name).
            Initalized to an empty dict.
        filledValueInRun (bool): Can be set when a value is filled in a run. It is the user's responsibility to
            set the value to ``True`` when desired. The flag will be reset to ``False`` at the start of each run.
            Initialized to ``False``.
        runLength (int): Length of the current run in minutes.

    Note:
        Arguments listed above are also available to be called as members. However, it is greatly preferred to access
        hists through the methods listed below.

    Note:
        You can draw on the histogram that you are processing by passing ``"same"`` as a parameter to the ``Draw()``.

    """

    def __init__(self, firstRun, lastRun, runDirs, qaFunctionName):
        """ Initializes the container with all of the requested information. """
        self.firstRun = firstRun
        self.lastRun = lastRun
        self.runDirs = runDirs
        self.qaFunctionName = qaFunctionName
        self.hists = {}
        self.currentRun = firstRun
        self.filledValueInRun = False
        self.currentRunLength = 0

    def addHist(self, hist, label):
        """ Add a histogram at a given label.

        Note:
            This function calls ``SetDirectory(0)`` on the passed histogram to make sure that it is not
            removed when it goes out of scope.

        Args:
            hist (TH1): The histogram to be added.
            label (str): 

        Returns:
            None
        """
        # Ensures that the created histogram does not get destroyed after going out of scope.
        hist.SetDirectory(0)
        self.hists[label] = hist

    def addHists(self, hists):
        """ Add histograms from a dict containing histograms with keys set as the labels.

        Args: 
            hists (dict): Dictionary with the hist labels as keys and the histograms as values.

        Returns:
            None
        """

        for hist, label in zip(hists, labels):
            self.addHist(hist, label)

    def getHist(self, histName):
        """ Gets a histogram labeled by name.

        Args:
            histName (str): Label of the desired histogram. Often the hist name.

        Returns:
            TH1: The requested histogram or None if it doesn't exist.

        """
        return self.hists.get(histName, None)

    def getHists(self):
        """ Gets all histograms and returns them in a list.

        Args:
            None

        Returns:
            list: List of TH1s, generated by getting ``values()`` of the ``hists`` dict.

        """
        return self.hists.values()

    def getHistLabels(self):
        """ Gets all histogram labels and returns them in a list.

        Args:
            None

        Returns:
            list: List of strings, generated by getting ``keys()`` of the ``hists`` dict.

        """
        return self.hists.keys()

    def getHistsDict(self):
        """ Gets the dict stored by the class.

        Args:
            None

        Returns:
            dict: Contains histograms with keys equal to the histogram label (often the hist name).
        """
        return self.hists

###################################################
def checkHist(hist, qaContainer):
    """ Selects and calls the proper qa function based on the input.

    Args:
        hist (TH1): The histogram to be processed.
        qaContainer (:class:`~processRunsModules.qa.qaFunctionContainer`): Contains information about the qa
            function and histograms, as well as the run being processed.

    Returns:
        bool: Returns true if the histogram that is being processed should not be printed.
            This is usually true if we are processing all hists to extract a QA value and 
            usually false if we are trying to process all hists to check for outliers or 
            add a legend or check to a particular hist.
    """
    #print "called checkHist()"
    skipPrinting = False
    if qaContainer is not None:
        # Python functions to apply for processing a particular QA function
        # Only a single function is selected on the QA page, so no loop is necessary
        # (ie only one call can be made).
        skipPrinting = getattr(currentModule, qaContainer.qaFunctionName)(hist, qaContainer)
    else:
        # Functions to always apply when processing
        # We loop here because multiple functions could be desired here
        # We do not want to skip printing here, so the default value is fine and
        # the return value is ignored.
        for functionName in processingParameters.qaFunctionsToAlwaysApply:
            #print dir(currentModule)
            getattr(currentModule, functionName)(hist)

    return skipPrinting

###################################################
# Load detector functions from other modules
###################################################
#print dir(currentModule)
# For more details on how this is possible, see: https://stackoverflow.com/a/3664396
detectorsPath = processingParameters.detectorsPath
modulesPath = processingParameters.modulesPath
print("\nLoading modules for detectors:")

# For saving and show the docstrings on the QA page.
qaFunctionDocstrings = {}

# We need to combine the available subsystems. subsystemList is not sufficient because we may want QA functions
# but now to split out the hists on the web page.
# Need to call list so that subsystemList is not modified.
# See: https://stackoverflow.com/a/2612815
subsystems = list(processingParameters.subsystemList)
for subsystem in processingParameters.qaFunctionsList:
    subsystems.append(subsystem)

# Make sure that we have a unique list of subsystems.
subsystems = list(set(subsystems))

# Load functions
for subsystem in subsystems:
    print("Subsystem", subsystem, "Functions loaded:", end=' ') 

    # Ensure that the module exists before trying to load it
    if os.path.exists(os.path.join(modulesPath, detectorsPath, "%s.py" % subsystem)):
        #print "file exists"
        # Import module dynamically
        subsystemModule = importlib.import_module("%s.%s.%s" % (modulesPath, detectorsPath, subsystem))

        # Loop over all functions from the dynamically loaded module
        # See: https://stackoverflow.com/a/4040709
        functionNames = []
        for funcName in inspect.getmembers(subsystemModule, inspect.isfunction):
            # Contains both the function name and a reference to a pointer. We only want the name,
            # so we take the first element
            funcName = funcName[0]
            func = getattr(subsystemModule, funcName)

            # Add the function to the current module
            setattr(currentModule, funcName, func)

            # Save the function name so that it can be printed
            functionNames.append(funcName)
            
            # Save the function name so it can be shown on the QA page
            if subsystem in processingParameters.qaFunctionsList:
                if funcName in processingParameters.qaFunctionsList[subsystem]:
                    # Retreive the docstring
                    functionDocstring = inspect.getdoc(func)

                    # Remove anything after and including "Args", since it is not interesting
                    # on the QA page.
                    functionDocstring = functionDocstring[:functionDocstring.find("\nArgs:")]

                    # Save the docstring
                    qaFunctionDocstrings[subsystem + funcName] = [subsystem, functionDocstring]

        # Print out the function names that have been loaded
        if functionNames != []:
            print(", ".join(functionNames))
        else:
            print("")
    else:
        print("")

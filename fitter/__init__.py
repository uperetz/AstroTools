import re
from numpy import array, finfo

class Fitter(object):
    from ._plotdefs import CHANNEL,ENERGY,WAVE
    def __init__(self, data = None, resp = None, noinit = False, text = None):
        self.axisz     = None
        self.dataz     = None
        self.ptype     = self.CHANNEL
        self.models    = []
        self.ionlabs   = []
        self.current   = None
        self.binfactor = 1
        self.result    = []
        self.xstart    = None
        self.xstop     = None
        self.ystart    = None
        self.ystop     = None
        self.plotmodel = array(())
        self.labelions = False
        self.area      = array(())
        self.eps       = finfo(float).eps
        self.stat      = self.chisq
        self.axisOverride=[None,None]
        if not noinit: self.initplot()
        if data is not None:
            self.loadData(data,text)
        if resp is not None:
            self.loadResp(resp)

    #Exceptions
    from ._datadefs import dataResponseMismatch, noIgnoreBeforeLoad
    from ._modeling import NotAModel
    from ._error    import errorNotConverging, newBestFitFound
    from ._plotdefs import badPlotType, badZoomRange, labelAxis,toggleLog
    from ._plotdefs import unlabelAxis, toggleIonLabels, plotEff

    #Methods
    from ._datadefs import loadResp, loadData, loadBack, loadAncr
    from ._datadefs import checkLoaded, transmit, ignore, notice, set_channels, reset
    from ._datadefs import untransmit, div, group, updateIonLabels
    from ._modeling import chisq,reduced_chisq,append,delete,cstat
    from ._modeling import activate,nameModel,energies,tofit,toMinimize,fit
    from ._error    import error
    from ._plotdefs import zoomto,rebin,setplot,plot,shift,removeShift
    from ._plotdefs import initplot,plotModel, plotDiv, toggle_area

    #Model wrappers
    def thaw(self, *params):
        self.current.thaw(*params)
    def freeze(self, *params):
        self.current.freeze(*params)
    def getThawed(self):
        return self.current.getThawed()
    def getParams(self):
        return self.current.getParams()
    def printParams(self):
        self.current.printParams()
    def initArgs(self):
        return self.current.initArgs()
    def tie(self,what,to):
        self.current.tie(what,to)
    def is_tied(self,index,param):
        return self.current.is_tied(index,param)
    def setp(self,pDict):
        self.current.setp(pDict)
    def setStat(self,s):
        self.stat = s
    def calc(self,pDict = {}):
        self.setp(pDict)
        self.result = self.tofit(self.energies())
        self.plot()


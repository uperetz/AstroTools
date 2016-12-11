from fitshandler import Response,Data,FakeResponse
from os.path     import dirname,join

class dataResponseMismatch(Exception): pass
class noIgnoreBeforeLoad(Exception): pass

def div(self,other):
    try: self.division = list(self.data/other)
    except AttributeError:
        self.division = list(self.data/Data(other))

def loadResp(self,resp):
    self.resp      = Response(resp)
    self.checkLoaded()
    self.resp_file = resp
    self.ionlabs   = []
    ions           = iter(self.ionlocations)
    ebounds        = self.resp.ebounds
    channeliter    = iter(range(len(ebounds)))
    try:
        while True:
            channel= channeliter.next()
            ion    = ions.next()
            energy = Response.keVAfac/ion[0]
            while energy > ebounds[channel][1]:
                ion    = ions.next()
                energy = Response.keVAfac/ion[0]
            while energy < ebounds[channel][0]:
                channel= channeliter.next()
            self.ionlabs.append((channel+1,energy,ion[0],ion[1]))
    except StopIteration: pass

def loadData(self,data, text = None):
    self.data  = Data(data, text=text)
    if self.data.resp is not None:
        try: self.loadResp(self.data.resp)
        except IOError: 
            self.loadResp(join(dirname(data),self.data.resp))
    elif text is not None:
        self.resp  = FakeResponse(self.data.channels)
    self.checkLoaded()
    self.plot(user = False)
    self.data_file = data
    try: self.untransmit()
    except AttributeError: pass

def loadBack(self,back):
    self.data.loadback(back)
    self.back_file = back

def checkLoaded(self):
    try: 
        if len(self.data.channels) != len(self.resp.matrix):
            raise self.dataResponseMismatch(len(self.data.channels),len(self.resp.matrix))
    except AttributeError: pass

def untransmit(self):
    self.data.untransmit()
    del(self.transmit_file)

def transmit(self, table):
    self.data.transmit(table)
    self.plot(user = False)
    self.transmit_file = table

def group(self,g):
    self.data.group(g)
    self.plot(user = False)

def ignore(self, minX, maxX):
    try:
        self.checkLoaded()
        for fitshandler in (self.data,self.resp):
            #Need to reset generator
            if self.ptype == self.CHANNEL: 
                channels = range(minX,maxX+1)
            if self.ptype == self.ENERGY : 
                channels = self.resp.energy_to_channel(minX, maxX)
            if self.ptype == self.WAVE: 
                channels    = self.resp.wl_to_channel(minX, maxX)
            fitshandler.ignore(channels)
        if self.area.any():
            self.area = self.resp.eff
        self.plot(user = False,keepannotations = True)
    except AttributeError:
        raise self.noIgnoreBeforeLoad()

def reset(self, zoom = True, ignore = True):
    if zoom:
        self.xstart = None
        self.xstop  = None
        self.ystart = None
        self.ystop  = None
    if ignore:
        for fitshandler in (self.data,self.resp):
            try:
                fitshandler.reset()
            except AttributeError: pass
        if self.area.any():
            self.area = self.resp.eff
    self.plot(user = False,keepannotations = True)


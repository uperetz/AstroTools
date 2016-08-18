
import fitsio
from numpy import int as ndint
from numpy import array,dot,inf,delete,sort,zeros,unravel_index,argmax

class fitsHandler(object): pass

class Response(fitsHandler):
    def __init__(self, response):
        self.ebounds     = [(elow,ehigh) for _,elow,ehigh in fitsio.read(response,ext=2)]
        self.ebins       = []
        self.ebinAvg     = []

        elow  = 0
        ehigh = 1
        ngrp  = 2
        fch   = 3
        nch   = 4
        row   = 5

        energies = []
        nchannels = fitsio.read_header(response,ext=1)['DETCHANS']
        data = list(fitsio.read(response,ext=1))
        for record in data:
            self.ebins.append(record[ehigh]-record[elow])
            self.ebinAvg.append((record[ehigh]+record[elow])/2.0)
            channel = 1
            ind = 0
            grps = record[ngrp]
            #Speed things up!!! Also - while kills speed for some reason.
            matrow = list(record[row])
            energies.append([])
            for start_channel,nchannel in zip(record[fch][:grps],record[nch][:grps]):
                for _ in range(channel,start_channel):
                    energies[-1].append(0)
                    channel += 1
                for _ in range(start_channel,start_channel+nchannel):
                    energies[-1].append(matrow[ind])
                    ind += 1
                    channel += 1
            for _ in range(channel,nchannels+1):
                channel += 1
                energies[-1].append(0)
        self.omatrix  = array(energies).transpose()
        self.reset() 
        self.ebins    = array(self.ebins)
        self.ebinAvg  = array(self.ebinAvg)

    def ignore(self, channels):
        self.deleted.update([c-1 for c in channels if c > 0 and c <= len(self.omatrix)])
        self.matrix = delete(self.omatrix,list(self.deleted), axis = 0)

    def reset(self):
        self.deleted = set()
        self.matrix  = array(self.omatrix,copy=True)

    def convolve_channels(self,vector):
        return dot(self.matrix,vector*self.ebins)

    keVAfac = 12.39842
    def energy(self,table = None, forwl = False, ignore = []):
        if ignore:
            for channel in range(len(self.omatrix)):
                e0,e1  = self.ebounds[channel]
                energy = (e0+e1)/2.0
                w0 = self.keVAfac/e1
                w1 = self.keVAfac/e0
                wl = self.keVAfac/energy
                if ignore[0] == ignore[1]:
                    if ((not forwl and e0 <= ignore[0] and e1 >= ignore[0]) or
                        (forwl and w0 <= ignore[0] and w1 >= ignore[0])):
                        yield channel + 1
                else:
                    if ((not forwl and energy >= ignore[0] and energy <= ignore[1]) or
                        (forwl and wl >= ignore[0] and wl <= ignore[1])):
                        yield channel + 1
        else:
            for row in table:
                if len(row) == 2:
                    channel,count = row
                else:
                    channel,count,error = row
                channel = int(channel - 1)
                energy = (self.ebounds[channel][1]+self.ebounds[channel][0])/2.0
                eerror = (self.ebounds[channel][1]-self.ebounds[channel][0])
                cts    = count/eerror
                if len(row) > 2: 
                    error  = error/eerror
                    yield [energy,eerror,cts,error]
                else:
                    if forwl:
                        yield [energy,eerror,cts]
                    else:
                        yield [energy,cts]

    def wl(self, table):
        for row in self.energy(table, True):
            E  = row[0]
            dE = row[1]
            dl = self.keVAfac*dE/E**2
            row[0] = self.keVAfac/row[0]
            if len(row) > 3:
                row[1] = dl
                row[2] = row[2]*dE/dl
                row[3] = row[3]*dE/dl
                yield row
            else:
                yield (row[0],row[2]*dE/dl)

class Data(fitsHandler):
    def __init__(self, data):
        data, h         = fitsio.read(data,header = True)
        self.exposure   = h['EXPOSURE']
        self.resp       = None
        try:
            self.resp   = h['RESPFILE']
        except AttributeError: pass
        self.ochannels  = []
        self.octs       = []
        self.ocounts    = []
        self.oscales    = []
        self.oerrors    = []

        CHANNEL = 0
        COUNTS  = 1
        QUALITY = 2
        AREASCAL= 3
       
        row = 1
        for record in data:
            counts  = record[COUNTS]
            self.ochannels.append(row)
            row += 1
            if record[QUALITY] > 0 or counts <= 0:
                counts = 0
                self.ocounts.append(0)
                self.oscales.append(0)
                self.octs.append(0)
                self.oerrors.append(inf)
            else:
                scale   = record[AREASCAL]
                self.ocounts.append(counts)
                self.oscales.append(scale)
                self.octs.append(counts/self.exposure/scale)
                self.oerrors.append(counts**0.5/self.exposure/scale)

        self.ochannels  = array(self.ochannels)
        self.octs       = array(self.octs)
        self.ocounts    = array(self.ocounts)
        self.oscales    = array(self.oscales)
        self.oerrors    = array(self.oerrors)
        self.reset()

    def reset(self):
        self.deleted  = set()
        self.channels = array(self.ochannels ,copy=True)
        self.cts      = array(self.octs      ,copy=True)
        self.counts   = array(self.ocounts   ,copy=True)
        self.scales   = array(self.oscales   ,copy=True)
        self.errors   = array(self.oerrors   ,copy=True)
        try:
            self.transmission = array(self.otransmission,copy=True)
        except AttributeError: pass

    def ignore(self,channels):
        self.deleted.update([c-1 for c in channels if c >= self.ochannels[0] and c <= self.ochannels[-1]])
        self.channels  = delete(self.ochannels ,list(self.deleted),axis = 0)
        self.cts       = delete(self.octs      ,list(self.deleted),axis = 0)
        self.counts    = delete(self.ocounts   ,list(self.deleted),axis = 0)
        self.scales    = delete(self.oscales   ,list(self.deleted),axis = 0)
        self.errors    = delete(self.oerrors   ,list(self.deleted),axis = 0)
        try:
            self.transmission  = delete(self.otransmission, list(self.deleted),axis = 0)
            self.cts    /= self.transmission
            self.errors /= self.transmission
        except AttributeError: pass

    def transmit(self,table):
        try:
            transmission = array([float(x) for x in open(table)])
        except IOError: transmission = array(table)
        self.otransmission = transmission
        self.transmission  = delete(self.otransmission, list(self.deleted),axis = 0)
        self.cts /= self.transmission

    def rebin(self,binfactor, model = None):
        cts = self.counts
        if model != None:
            cts  = model
        
        ind = 0
        while ind < len(self.channels):
            sums = [0,0,0]
            if model != None:
                sums = [0,0]

            start = 0
            scale = 0
            count = 0
            trans = 0
            while count < binfactor and ind < len(self.channels) and (not sums[0] or self.channels[ind]-self.channels[ind-1] == 1):
                scale   += self.scales[ind]
                sums[0] += self.channels[ind]
                sums[1] += cts[ind]
                count   += 1
                try: trans += self.transmission[ind]
                except AttributeError: pass
                ind += 1
           
            sums[0] /= float(count)
            if model == None:
                if not scale: continue
                sums[2] = sums[1]**0.5/self.exposure/scale
                sums[1] = sums[1]/self.exposure/scale
                if trans:
                    trans   /= float(count)
                    sums[1] = sums[1]/trans
                    sums[2] = sums[2]/trans
            else:
                sums[1] /= float(count)
            yield sums

class Events(fitsHandler):
    def __init__(self, event_file):
        self.events = sort(fitsio.read(event_file,columns=('x','y')))
        xmax        = self.events[-1][0]
        ymax        = max((a[1] for a in self.events))
        self.map    = zeros((ymax,xmax),dtype=ndint)

        X = 0
        Y = 1
        for event in self.events: 
            self.map[event[Y]-1][event[X]-1] += 1
           
    def centroid(self,ignore = ()):
        return tuple((x+1 for x in unravel_index(argmax(self.map),self.map.shape)[::-1]))

    def _validate_pixels(self,pixels,thresh):
        count = valid = 0
        for value in pixels:
            count += 1
            if value >= thresh: valid += 1
        return count,valid

    def is_effective_radius(self,center,R, thresh = None):
        if thresh == None:
            thresh = self[center]/20.0
        X,Y = center
        count = valid = 0
        for pixels in ((self[(X-R,y)] for y in range(Y-R,Y+R+1)),
            (self[(X+R,y)] for y in range(Y-R,Y+R+1)),
            (self[(x,Y-R)] for x in range(X-R+1,X+R)),
            (self[(x,Y+R)] for x in range(X-R+1,X+R))):
            res = self._validate_pixels(pixels,thresh)
            count += res[0]
            valid += res[1]
        return valid/float(count) >= 0.5

    def object(self):
        R = 0
        center = self.centroid()
        while self.is_effective_radius(center,R): R += 1
        return center+(R,)

    def background(self, outer_coefficient = 2):
        x,y, Rmin = self.object()
        return x,y,Rmin,Rmin*outer_coefficient

    def __iter__(self): 
        self.iter = 0
        return self

    def next(self):
        if self.iter == len(self.events): raise StopIteration()
        self.iter += 1
        return self.events[self.iter - 1]

    def __getitem__(self,coords):
        return self.map[coords[1]-1][coords[0]-1]


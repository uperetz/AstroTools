#!/usr/bin/env python3
'''
Created on Mar 15, 2013

@author: kabanus
'''
if True or __name__ == "__main__":
    from argparse import ArgumentParser
    import os
    import re
    from sys import argv
    bellfile = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'bell.wav')
    if os.name == 'nt':
        # Windows ctrl-c and ring handling
        try:
            import win32api
            import _thread
            import ctypes
            import imp
            import winsound

            def ring(b=bellfile):
                winsound.PlaySound(b, winsound.SND_FILENAME)

            basepath = imp.find_module('numpy')[1]
            ctypes.CDLL(os.path.join(basepath, 'core', 'libmmd.dll'))
            ctypes.CDLL(os.path.join(basepath, 'core', 'libifcoremd.dll'))

            def handler(dwCtrlType, hook_sigint=_thread.interrupt_main):
                if dwCtrlType == 0:  # CTRL_C_EVENT
                    hook_sigint()
                    return 1
                return 0  # chain to the next handler
            win32api.SetConsoleCtrlHandler(handler, 1)
        except (ImportError, WindowsError):
            print(("Warning: win32api  module  not found, you will  not be able to Ctlr-C  calculations. To fix\n" +
                   "this try 'pip installPyWin32'  from  any   terminal,  or download and  install binary  from\n" +
                   "https://sourceforge.net/projects/pywin32/files/pywin32/. This warning may also be generated\n" +
                   "on Windows machines if numpy or something close is missing."))
    else:
        from wave import open as waveOpen
        import ossaudiodev
        from ossaudiodev import open as ossOpen
        try:
            dsp = ossOpen('w')
            dsp.close()

            def ring(b=bellfile):
                s = waveOpen(b, 'rb')
                (nc, sw, fr, nf, comptype, compname) = s.getparams()
                try:
                    from ossaudiodev import AFMT_S16_NE
                except ImportError:
                    from sys import byteorder
                    if byteorder == "little":
                        AFMT_S16_NE = ossaudiodev.AFMT_S16_LE
                    else:
                        AFMT_S16_NE = ossaudiodev.AFMT_S16_BE
                dsp.setparameters(AFMT_S16_NE, nc, fr)
                data = s.readframes(nf)
                s.close()
                dsp.write(data)
                dsp.close()
        except FileNotFoundError:
            def ring(b=None): return
            print('Warning: Could not find audio output device, no beep will be beeped.')

    import tkinter.messagebox as messagebox
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from tkinter import Tk, StringVar, LEFT, TOP, N, S, E, W, Label, BOTH
    from tkinter.messagebox import askquestion
    from AstroTools.fitshandler import Data
    from AstroTools.plotInt import Iplot, plt
    from fitter import Fitter
    from fitter.gui.modelReader import modelReader
    from fitter.gui.simplewindows import runMsg
    from fitter.gui.entrywindows import ignoreReader, rebinReader, varReader
    from fitter.gui.parameterframe import parameterFrame
    from fitter.gui.helperfunctions import make_frames, getfile
    from fitter.gui.gui import Gui
    ALL = N + S + W + E
    Iplot.quiet()

    class App(object):
        debug = False
        xspec_packages = []

        def __init__(self, h=500, w=800, b=5):
            self.root = Tk()
            self.root.wm_title("The amazing fitter!")
            self.border = b
            self.width = 800
            self.height = 500
            self.fitter = Fitter(noinit=True)
            self.thawedDict = {}
            self.statistic = StringVar()
            self.statistic.set(u"Reduced \u03C7\u00B2: Not calculated yet.")
            self.fstatistic = StringVar()
            self.fstatistic.set(u"\u03C7\u00B2 = Not calculated yet.")
            self.ignored = StringVar()
            self.ignored.set("Ignored:")
            self.grouped = StringVar()
            self.grouped.set("Grouped: 1")
            self.model = ""
            self.datatitle = StringVar()
            self.datatitle.set("No active model")
            self.respfile = StringVar()
            self.respfile.set("")
            self.ancrfile = StringVar()
            self.ancrfile.set("")
            self.datafile = StringVar()
            self.datafile.set("")
            self.backfile = StringVar()
            self.backfile.set("")
            self.transfile = StringVar()
            self.transfile.set("")
            self.paramLabels = {}
            self.ranfit = False
            self.errors = {}

            make_frames(self)
            self.params = parameterFrame(self, self.canvasDataFrame, self.data_frame)
            self.params.draw()

            self.root.bind("<Key-Escape>", self._quit)
            self.root.protocol('WM_DELETE_WINDOW', self._quit)

            self.canvas = FigureCanvasTkAgg(plt.get_current_fig_manager().canvas.figure, master=self.main)
            nav = NavigationToolbar2Tk(self.canvas, self.main)
            # Only load figure after manager has been set
            self.fitter.initplot(font_size=16)
            for child in nav.winfo_children():
                child.configure(takefocus=False)
            Label(nav, textvar=self.datafile, padx=self.border).pack(side=LEFT)
            Label(nav, textvar=self.respfile, padx=self.border).pack(side=LEFT)
            Label(nav, textvar=self.backfile, padx=self.border).pack(side=LEFT)
            Label(nav, textvar=self.ancrfile, padx=self.border).pack(side=LEFT)
            Label(nav, textvar=self.transfile, padx=self.border).pack(side=LEFT)
            Gui(self, self.gui)
            self.canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

            self.refreshPlot()

            self.root.rowconfigure(0, weight=1)
            self.root.columnconfigure(0, weight=1)
            # For windows
            self.root.focus_force()
            self.root.mainloop()

        def refreshPlot(self):
            self.canvas.draw()

        def loadModel(self):
            try:
                self.modelload.root.destroy()
            except AttributeError:
                pass
            self.modelload = modelReader(self)

        def setStat(self, s):
            l, func = {'C': ('C stat', self.fitter.cstat), 'chisq': (u'\u03C7\u00B2', self.fitter.chisq)}[s]
            self.fitter.setStat(func)
            try:
                self.fstatistic.set('{} = {}'.format(l, self.fitter.stat(self.fitter.result)))
            except AttributeError:
                self.fstatistic.set('{} = {}'.format(l, "Not calculated yet."))

        def modelLoaded(self):
            self.datatitle.set(self.fitter.current)
            self.calc(draw=False)
            self.params.draw()

        def toggleParam(self, index, param):
            if self.thawedDict[(index, param)][0].get():
                self.fitter.thaw((index, param))
            else:
                self.fitter.freeze((index, param))

        def dumpParams(self):
            cmd = ""
            for (index, param), value in self.fitter.getParams():
                cmd += str(index) + ':' + param + " = "
                tied = self.fitter.is_tied(index, param)
                if tied:
                    cmd += str(tied[0]) + ":" + tied[1] + ','
                else:
                    cmd += str(value) + ','
            for (index, param) in sorted(self.thawedDict):
                if self.thawedDict[(index, param)][0].get():
                    cmd += 'thaw ' + str(index) + ':' + param + ','
            return cmd[:-1]

        def dumpParamCmd(self):
            try:
                self.commandline.dump(self.dumpParams())
            except AttributeError:
                pass

        def loadSession(self, keyword=None):
            init = {}
            fname = getfile('fsess')
            if not fname:
                return
            try:
                for line in open(fname):
                    index = line.index(':')
                    init[line[:index]] = line[index + 1:].strip('\n').strip()
            except ValueError:
                messagebox.showerror("Failed to load session!", 'Bad format, wrong file?')
                if self.debug:
                    raise
                return
            root = os.path.dirname(fname)
            root = root + '/' if root else './'
            for k, action in (
                    ('data', lambda: self.load(self.fitter.loadData, root + init['data'])),
                    ('resp', lambda: self.load(self.fitter.loadResp, root + init['resp'])),
                    ('tran', lambda: self.load(self.fitter.transmit, root + init['tran'])),
                    ('ptype', lambda: self.fitter.setplot(int(init['ptype'])))
               ):
                try:
                    if keyword is None or keyword == k:
                        action()
                except (KeyError, AttributeError):
                    pass

            if keyword is None or keyword == "xspecpackages":
                try:
                    pkgs = init['xspecpackages'].split(',')
                    for i in range(0, len(pkgs), 2):
                        if [pkgs[i], pkgs[i + 1]] not in self.xspec_packages:
                            self.xspec_packages.append([pkgs[i], pkgs[i + 1]])
                except KeyError:
                    pass

            if keyword is None or keyword == "Grouped":
                try:
                    group = init['Grouped']
                    ig = rebinReader(self, group=True, gui=False)
                    ig.parse(group)
                except (KeyError, AttributeError):
                    pass

            if keyword is None or keyword == "Ignored":
                try:
                    ignored = init['Ignored']
                    ig = ignoreReader(self, 'ignore', gui=False)
                    ig.parse(ignored)
                except (KeyError, AttributeError):
                    pass
                except Exception:
                    messagebox.showerror("Failed to load session!", 'Got ignore channels, but no data')
                    if self.debug:
                        raise
                    return

            if keyword is None or keyword == "model":
                try:
                    model = modelReader(self, False)
                    init['model'] = re.sub(r'Table\("[^/]', 'Table("' + root, init['model'])
                    model.parse(init['model'])
                    self.commandline.parseCmd(init['param'])
                    e = init['errors'].split(',')
                    self.ranfit = True
                    length = 4
                    for index, param, mine, maxe in ([e[n] for n in range(i, i + length)]
                                                     for i in range(0, len(e), length)):
                        iparam = (int(index), param)
                        self.errors[iparam] = (float(mine), float(maxe))
                        error = (self.errors[iparam][1]-self.errors[iparam][0])/2.0
                        self.thawedDict[iparam][1].set('(%.2E)' % error)
                        self.paramLabels[iparam][2].configure(relief='flat', state='disabled')
                except ZeroDivisionError:
                    if self.debug:
                        raise
                    messagebox.showerror('Failed to load session model!', 'Likely all channels ignored somehow')
                except AttributeError as e:
                    if 'Xspec' in str(e):
                        messagebox.showerror('Failed to load session model!',
                                             'Model contains Xspec component, but heasarc not detected!')
                    else:
                        raise
                except KeyError:
                    pass
                finally:
                    try:
                        model.destroy()
                    except Exception:
                        pass
            self.refreshPlot()

        def saveSession(self, name, extension):
            with open(name + '.' + extension, 'w') as fd:
                def writeline(string):
                    fd.write(string + '\n')

                try:
                    writeline('data:' + self.fitter.data_file)
                except AttributeError:
                    pass
                try:
                    writeline('resp:' + self.fitter.resp_file)
                except AttributeError:
                    pass
                try:
                    writeline('tran:' + self.fitter.transmit_file)
                except AttributeError:
                    pass
                try:
                    writeline('ptype:' + str(self.fitter.ptype))
                except AttributeError:
                    pass
                try:
                    writeline(self.ignored.get())
                except AttributeError:
                    pass
                try:
                    writeline(self.grouped.get())
                except AttributeError:
                    pass
                try:
                    writeline('model:' + self.fitter.current.__str__())
                except AttributeError:
                    pass
                try:
                    writeline('param:' + self.dumpParams())
                except AttributeError:
                    pass
                if self.errors:
                    writeline(
                        'errors:' + str(self.errors).translate(str.maketrans(
                                                '', '', "(){} '")).replace(':', ','))
                if self.xspec_packages:
                    writeline(
                        'xspecpackages:' + str(self.xspec_packages).translate(str.maketrans(
                                                '', '', "[] '")))

        def saveParams(self, name, extension):
            if extension:
                name += '.' + extension
            params = [param.split('=')
                      for param in self.dumpParams().split(',')
                      if param[0] != 't' and param[1] != 'f']

            for i in range(len(params)):
                index, param = params[i][0].split(':', 1)
                index = int(index)
                param = param.strip()
                try:
                    try:
                        # Look for measured error
                        err = self.errors[(index, param)]
                        params[i] = '%3d %10s = %s (%.3E, + %.3E)' % (index, param, params[i][1], err[0], err[1])
                    except KeyError:
                        # Settle for standard error
                        err = self.fitter.stderr[(index, param)]
                        params[i] = u'%3d %10s = %s \u00B1 %.3E' % (index, param, params[i][1], err)
                except (KeyError, AttributeError):
                    # Guess this has no error
                    params[i] = '%3d %10s = %s' % (index, param, params[i][1])

            params.append(self.statistic.get())
            params.append(self.ignored.get())
            params.append(self.grouped.get())
            params.insert(0, self.datatitle.get())

            with open(name, 'w') as paramFile:
                for p in params:
                    paramFile.write(p + '\n')

        def load(self, what, res=None, user=True, name=None):
            if res is None:
                res = getfile('pha', 'FTZ', 'FIT', 'ds', 'dat', 'RMF', 'RSP')
            if not res:
                return
            if name is None:
                name = what.__name__[-4:]
            m = runMsg(self, "Loading {}...".format(name))
            try:
                Iplot.clearPlots()
                what(res)
            except OSError as e:
                if type(e) is FileNotFoundError:
                    messagebox.showerror('File not found!', str(e))
                else:
                    what(res, text=True)
            except Data.MultipleDevices as e:
                devices = [int(x) for x in str(e).split()[-1].strip('().').split('-')]
                m.destroy()
                z = runMsg(self, 'Attempting to load multiple device fits file - please select valid device')
                varReader(self, 'Device ({}-{})'.
                          format(*devices), type=int, catch=True,
                          action=lambda dev, z=z: what(d=res, dev=dev) or z.destroy())
                return
            except (ValueError, IOError, KeyError) as e:
                messagebox.showerror('Bad file!', 'Please check file is correct format:\n' + str(e))
                if self.debug:
                    raise
                return
            except Data.lengthMismatch as e:
                messagebox.showerror('Mismatch!', 'Please file and data match:\n' + str(e))
                if self.debug:
                    raise
                return
            except Exception as e:
                if str(e).find('ndarray') > -1:
                    messagebox.showerror('Bad file!', 'Tranmission and data have a different amount of channels!')
                else:
                    raise
                if self.debug:
                    raise
                return
            finally:
                m.destroy()
            if self.fitter.current is not None:
                self.calc()
            try:
                self.transfile.set('Transmission: ' + self.fitter.transmit_file.split('/')[-1])
            except AttributeError:
                self.untransmit(label_only=True)
            try:
                self.respfile.set('Response: ' + self.fitter.resp_file.split('/')[-1])
            except AttributeError:
                pass
            try:
                self.backfile.set('BG: ' + self.fitter.back_file.split('/')[-1])
            except AttributeError:
                pass
            try:
                self.datafile.set('Data: ' + self.fitter.data_file.split('/')[-1])
            except AttributeError:
                pass
            try:
                self.ancrfile.set('Ancillary: ' + self.fitter.ancr_file.split('/')[-1])
            except AttributeError:
                pass

        def getError(self, *args):
            cont = False
            if not self.ranfit:
                messagebox.showerror('Why would you want to?!', 'Run fit before calculating errors')
                if self.debug:
                    raise
                return not cont
            try:
                # Message construct used so beep is heard before message,
                # and save return on each one.
                m = runMsg(self)
                for iparam in args:
                    index, param = iparam
                    index = int(index)
                    err = ''
                    self.errors[iparam] = self.fitter.error(index, param)
                    error = (self.errors[iparam][1]-self.errors[iparam][0])/2.0
                    self.thawedDict[(index, param)][1].set('(%.2E)' % error)
                    self.paramLabels[(index, param)][2].configure(relief='flat', state='disabled')
            except (ValueError, KeyError):
                title, err, cont = (str(index) + ':' + param + ': No such parameter!', 'Check yourself', True)
            except KeyboardInterrupt:
                title, err = ('Halt', "Caught Keyboard - thawed parameters may have changed.")
            except (self.fitter.errorNotConverging, RuntimeError):
                title, err = (str(index) + ':' + param + ': Error not converging!',
                              'Statistic insensitive to parameter')
            except self.fitter.newBestFitFound:
                title, err = ('Error not converging!', "Found new best fit! Space not convex.")
                self.params.resetErrors()
                self.ranfit = False
                self.params.relabel()
            finally:
                m.destroy()
                self.ring()
                if err:
                    messagebox.showerror(title, err)
                return not cont

        def ring(self):
            ring()

        def calc(self, draw=True):
            m = runMsg(self)
            try:
                if not self.fitter.plotmodel.any():
                    self.fitter.checkLoaded()
                    self.fitter.calc()
                else:
                    self.fitter.plotModel()
                self.refreshPlot()
            except (AttributeError, self.fitter.dataResponseMismatch):
                pass
            finally:
                if draw:
                    self.params.relabel()
                    self.params.resetErrors()
                self.ranfit = False
                self.ring()
                m.destroy()

        def untransmit(self, label_only=False):
            self.transfile.set("No transmission")
            self.transmit_file = ""
            if label_only:
                return
            self.doAndPlot(self.fitter.untransmit)

        def runFit(self):
            try:
                thawed = self.fitter.current.getThawed()
                if not thawed:
                    messagebox.showerror('Failed fit!', "No thawed parameters!")
                    if self.debug:
                        raise
                    return
            except AttributeError:
                    messagebox.showerror('Failed fit!', "No model loaded!")
                    if self.debug:
                        raise
                    return
            m = runMsg(self)
            try:
                self.doAndPlot(self.fitter.fit)
                self.ranfit = True
            except AttributeError:
                messagebox.showerror('Failed fit!', "No fitting method!")
                if self.debug:
                    raise
            except ValueError as e:
                if not str(e).startswith("-E- Failed fit with:"):
                    raise
                messagebox.showerror('Failed fit!', str(e).split(':', 1)[1])
            except RuntimeError:
                messagebox.showerror('Failed fit!', "Can't converge, too many free parameters?")
                if self.debug:
                    raise
            except Exception as e:
                messagebox.showerror('Failed fit!', e)
                raise
            finally:
                self.params.relabel()
                self.params.resetErrors()
                self.ring()
                m.destroy()
            try:
                for index, param in thawed:
                    self.thawedDict[(index, param)][1].set('(%.2E)' % self.fitter.stderr[(index, param)])
            except (KeyError, AttributeError):
                pass
            self.params.relabel()

        def doAndPlot(self, func, calcIgnore=False):
            try:
                func()
            except AttributeError as e:
                messagebox.showerror('Failed', 'No model/data/resp loaded\n\n' + str(e))
                if self.debug:
                    raise
                return
            except KeyboardInterrupt:
                messagebox.showerror('Halt', "Caught Keyboard")
            except Exception as e:
                messagebox.showerror('Failed', e)
                raise
            self.refreshPlot()
            # In case we changed axes, change ignore values to fit
            try:
                if calcIgnore:
                    ignoreReader(self, 'ignore', False).parse("")
            except AttributeError:
                pass

        def resetIgnore(self):
            self.fitter.reset(zoom=False)
            self.ignored.set("Ignored:")

        def _quit(self, event=None):
            if askquestion("Exit", "Sure?") == 'no':
                return
            self.root.quit()
            self.root.destroy()

    parser = ArgumentParser("Fitter Gui")
    parser.add_argument('--xspec-packages', '-x', nargs='*', default=[],
                        help='List of local packages for XSPEC (using lmod). ' +
                        'Path must follow model if the local model directory is not set in Xspec.init.')
    parser.add_argument('--debug', '-d', action="store_true", help='Add debug stuff to help locate errors.')

    opt = parser.parse_args(argv[1:])
    App.debug = opt.debug
    reading_package = 0
    for package in opt.xspec_packages:
        if not reading_package:
            App.xspec_packages.append([package])
        else:
            if os.path.isdir(package):
                App.xspec_packages[-1].append(package)
            else:
                App.xspec_packages[-1].append('')
                App.xspec_packages.append([package])
                reading_package = 0
        reading_package = 1 - reading_package
    if App.xspec_packages and len(App.xspec_packages[-1]) == 1:
        App.xspec_packages[-1].append('')
    App()

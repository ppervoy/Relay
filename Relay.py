#!/usr/bin/env python3
import configparser
import zlib
import schedule
import time
import datetime
from astral import Astral
from bottle import route, run
import threading
import logging
from termcolor import colored

configFile = "Relay.ini"
myCity = ""
myDepression = ""
myAddress = "localhost"
myPort = "80"
mySwitches = list()

class Switch:
    _Name = ""
    _GPIOchannel = 0
    _Type = "Sun"
    _timeOn = ""
    _timeOff = ""
    
    def jobRelayOn(self):
        print(colored("{} turned on {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'green'))

    def jobRelayOff(self):
        print(colored("{} turned off {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'red'))
    
    def Start(self):
        logging.info("'{}' started using {} on {}, off {}".format(self.Name, self.GPIOchannel, self.timeOn, self.timeOff))
        schedule.every().day.at(str(self.timeOn)).do(self.jobRelayOn)
        schedule.every().day.at(str(self.timeOff)).do(self.jobRelayOff)
        
    def Stop(self):
        print ("{} stopped".format(self.Name))
        schedule.clear(self.Name)

def crc(fileName):
    prev = 0
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)

configCRC = crc(configFile)

def LoadConfig(file = configFile):
    config = configparser.RawConfigParser()
    config.read(file)

    for e in config.sections():
        if e == "Global":
            for name, value in config.items(e):
                if name == "city":
                    global myCity
                    myCity = value
                elif name == "depression":
                    global myDepression
                    myDepression = value
                elif name == "address":
                    myAddress = value
                elif name == "port":
                    myPort = value
        else:
            s = Switch()
            s.Name = e
            for name, value in config.items(e):
                if name=="type":
                    s.Type = value
                elif name=="gpiochannel":
                    s.GPIOchannel = value
                elif name=="timeon":
                    s.timeOn = value
                elif name=="timeoff":
                    s.timeOff= value
            mySwitches.append(s)
    
    a = Astral()
    a.solar_depression = myDepression
    city = a[myCity]
    
    sun = city.sun(date=datetime.date(datetime.datetime.today().year, datetime.datetime.today().month, datetime.datetime.today().day), local=True)
    duskh = str(sun['dusk'])[11:13]
    duskm = str(sun['dusk'])[14:16]
    dusk = duskh + ":" + duskm
    
    dawnh = str(sun['dawn'])[11:13]
    dawnm = str(sun['dawn'])[14:16]
    dawn =  dawnh + ":" + dawnm
    
    for s in mySwitches:
        if s.Type == "Sun":
            s.timeOn = dusk
            s.timeOff = dawn

        s.Start()



@route('/')
def hello():
    s = mySwitches.count
    return str(s)
    
@route('/get_temp')
def getTemp():
    temp = "36.6"
    return temp



def jobUpdateAstral():
    a = Astral()
    a.solar_depression = myDepression
    city = a[myCity]
    
    sun = city.sun(date=datetime.date(datetime.datetime.today().year, datetime.datetime.today().month, datetime.datetime.today().day), local=True)
    duskh = str(sun['dusk'])[11:13]
    duskm = str(sun['dusk'])[14:16]
    dusk = duskh + ":" + duskm
    
    dawnh = str(sun['dawn'])[11:13]
    dawnm = str(sun['dawn'])[14:16]
    dawn =  dawnh + ":" + dawnm
    
    for s in mySwitches:
        if s.Type == "Sun":
            s.Stop()
            s.timeOn = dusk
            s.timeOff = dawn
            s.Start()
    


def jobCheckConfig():
    global configCRC
    if configCRC == crc(configFile):
        logging.info('Configuration unchaged')
    else:
        logging.info('Configuration chaged!! Reloading...')
        for s in mySwitches:
            s.Stop()
            del s
        #mySwitches.clear()
        
        LoadConfig()
        configCRC = crc(configFile)

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

LoadConfig()
schedule.every(1).seconds.do(jobCheckConfig)
schedule.every(2).seconds.do(jobUpdateAstral)

def jobStartWebServer():
    logging.info('...in job')
    run(host='10.0.1.11', port=80, debug=True)

#x = threading.Thread(target=jobStartWebServer)
#logging.info('Staring thread...')
#x.start

while 1:
    schedule.run_pending()
    time.sleep(1)
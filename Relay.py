#!/usr/bin/env python3
import configparser
import zlib
import schedule
import time
import datetime
from astral import Astral

configFile = "Relay.ini"
myCity = ""
myDepression = ""
mySwitches = list()

class Switch:
    _Name = ""
    _GPIOchannel = 0
    _Type = "Sun"
    _timeOn = ""
    _timeOff = ""
    
    def jobRelayOn(self):
        print("{} turned on {}, type {}".format(self.Name, self.GPIOchannel, self.Type))

    def jobRelayOff(self):
        print("{} turned off {}, type {}".format(self.Name, self.GPIOchannel, self.Type))
    
    def Start(self):
        print ("'{}' started using {} on {}, off {}".format(self.Name, self.GPIOchannel, self.timeOn, self.timeOff))
        #schedule.every(1).seconds.do(self.Blink).tag(self.Name)
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
                    myCity = value
                elif name == "depression":
                    myDepression = value
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

        # print ('Switch {} using GPIO#{}'.format(s.Name, s.GPIOchannel))
        s.Start()

def jobCheckConfig():
    global configCRC
    if configCRC == crc(configFile):
        print('Configuration unchaged')
    else:
        print('Configuration chaged!! Reloading...')
        for s in mySwitches:
            s.Stop()
            del s
        mySwitches.clear()
        
        LoadConfig()
        configCRC = crc(configFile)

LoadConfig()
schedule.every(30).seconds.do(jobCheckConfig)

while 1:
    schedule.run_pending()
    time.sleep(30)
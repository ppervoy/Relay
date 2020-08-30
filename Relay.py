#!/usr/bin/env python3
import configparser
import zlib
import schedule
import time

configFile = 'Relay.ini'
mySwitches = list()

class Switch:
    _Name = ""
    _GPIOchannel = 0
    _Type = "Sun"
    
    def Start (self):
        print ("{} started".format(self.Name))
        
    def Stop (self):
        print ("{} stopped".format(self.Name))

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
        s = Switch()
        s.Name = e
        for name, value in config.items(e):
            if name=="type":
                s.Type = value
            elif name=="gpiochannel":
                s.GPIOchannel = value
        mySwitches.append(s)
    
    for s in mySwitches:
        print ('Switch {} using GPIO#{}'.format(s.Name, s.GPIOchannel))

def jobCheckConfig():
    global configCRC
    if configCRC == crc(configFile):
        print('Configuration unchaged')
    else:
        print('Configuration chaged... Reloading')
        mySwitches.clear()
        LoadConfig()
        configCRC = crc(configFile)

LoadConfig()
schedule.every(1).seconds.do(jobCheckConfig)

while 1:
    schedule.run_pending()
    time.sleep(0.1)
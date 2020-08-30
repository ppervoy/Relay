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
    _On = ""
    _Off = ""
    
    def Blink (self):
        print("     * from {}".format(self.GPIOchannel))
    
    def Start (self):
        print ("'{}' started using {}".format(self.Name, self.GPIOchannel))
        schedule.every(1).seconds.do(self.Blink).tag(self.Name)
        
    def Stop (self):
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
        s = Switch()
        s.Name = e
        for name, value in config.items(e):
            if name=="type":
                s.Type = value
            elif name=="gpiochannel":
                s.GPIOchannel = value
        mySwitches.append(s)
    
    for s in mySwitches:
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
schedule.every(10).seconds.do(jobCheckConfig)



while 1:
    schedule.run_pending()
    time.sleep(0.1)
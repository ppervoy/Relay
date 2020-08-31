#!/usr/bin/env python3
import configparser
import zlib
import schedule
import time
import datetime
from astral import Astral
import logging
from termcolor import colored
import RPi.GPIO as GPIO



configFile = "Relay.ini"
myCity = ""
myDepression = ""
myAddress = ""
myPort = ""
mySwitches = list()



class Switch:
    _Name = ""
    _GPIOchannel = 0
    _Type = "Sun"
    _timeOn = ""
    _timeOff = ""
    
    def jobRelayOn(self):
        print(colored("{} turned on {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'green'))
        GPIO.output(int(self.GPIOchannel), GPIO.HIGH)

    def jobRelayOff(self):
        print(colored("{} turned off {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'red'))
        GPIO.output(int(self.GPIOchannel), GPIO.LOW)
    
    def Start(self):
        logging.info("'{}' started using {} on {}, off {}".format(self.Name, self.GPIOchannel, self.timeOn, self.timeOff))
        schedule.every().day.at(str(self.timeOn)).do(self.jobRelayOn).tag(self.Name)
        schedule.every().day.at(str(self.timeOff)).do(self.jobRelayOff).tag(self.Name)
        GPIO.setup(int(self.GPIOchannel), GPIO.OUT)
        
    def Stop(self):
        print(colored("{} stopped".format(self.Name), 'yellow'))
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
        
        LoadConfig()
        configCRC = crc(configFile)



format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.ERROR, datefmt="%H:%M:%S")
GPIO.setmode(GPIO.BCM)


    
if __name__ == '__main__':
    try:
        LoadConfig()
        schedule.every(1).seconds.do(jobCheckConfig)
        schedule.every(5).days.do(jobUpdateAstral)

        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
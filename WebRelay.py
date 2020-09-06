#!/usr/bin/env python3
import datetime
import zlib
import gevent
from gevent import monkey, spawn as gspawn, sleep as gsleep, socket, signal_handler as sig
monkey.patch_all()
import signal
import configparser
import logging
import schedule
import bottle
from bottle import get, request
from gevent.pywsgi import WSGIServer
# from geventwebsocket.handler import WebSocketHandler
import time
from astral import Astral
from termcolor import colored
import RPi.GPIO as GPIO

configFile = "Relay.ini"
myCity = ""
myDepression = ""
myAddress = "localhost"
myPort = "8080"
mySwitches = list()
serverStartTime = "1970/01/01 00:00"
serverLastInit = "1970/01/01 00:00"



class Switch:
    Name = ""
    GPIOchannel = 0
    Type = "Sun"
    Status = False
    timeOn = "00:00"
    timeOff = "00:01"
        
    def jobRelayOn(self):
        print(colored("{} turned on {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'green'))
        self.Status = True
        GPIO.output(int(self.GPIOchannel), GPIO.HIGH)

    def jobRelayOff(self):
        print(colored("{} turned off {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'red'))
        self.Status = False
        GPIO.output(int(self.GPIOchannel), GPIO.LOW)
    
    def Start(self):
        print(colored("Schedule \"{}\" started using {} on {}, off {}".format(self.Name, self.GPIOchannel, self.timeOn, self.timeOff), "blue"))
        schedule.every().day.at(str(self.timeOn)).do(self.jobRelayOn).tag(self.Name)
        schedule.every().day.at(str(self.timeOff)).do(self.jobRelayOff).tag(self.Name)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(int(self.GPIOchannel), GPIO.OUT)
        
    def Stop(self):
        print(colored("Schdeule \"{}\" stopped".format(self.Name), "blue"))
        schedule.clear(self.Name)



def crc(fileName):
    prev = 0
    
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)

configCRC = crc(configFile)



def loadConfig(file = configFile):
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
                    global myAddress
                    myAddress = value
                elif name == "port":
                    global myPort
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
        
    GPIO.setmode(GPIO.BCM)
    now = datetime.datetime.now()
    global serverLastInit
    serverLastInit = now.strftime("%Y/%m/%d %H:%M:%S")


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
    global mySwitches
    
    if configCRC == crc(configFile):
        print("Configuration unchaged")
    else:
        print("Configuration chaged!! Reloading...")
        for s in mySwitches:
            s.Stop()
            del s
        mySwitches *= 0
        
        loadConfig()
        configCRC = crc(configFile)



def setSchedule():
    schedule.every(5).seconds.do(jobCheckConfig)
    schedule.every(1).days.do(jobUpdateAstral)



def startServer():
    now = datetime.datetime.now()
    global serverStartTime
    serverStartTime = now.strftime("%Y/%m/%d %H:%M:%S")
    
    def start_thread():
        while True:
            try:
                schedule.run_pending()
            except Exception as e:
                print(str(e))
                
            gsleep(1)
                
    gspawn(start_thread)



@get('/')
def app():
    print("get /")
    global mySwitches
    
    try:
        toggleName = request.query["toggle"]
    except:
        toggleName = ""
    
    if toggleName:
        for s in mySwitches:
            if toggleName == s.Name:
                s.Type = "Manual"
                
                if s.Status:
                    s.jobRelayOff()
                else:
                    s.jobRelayOn()
    
    res = "<ul>"
    
    for s in mySwitches:
        res += "<li>" + s.Name + " (triggered by " + s.Type + ", on: " + s.timeOn + " off: " + s.timeOff + ") "
        
        if s.Status:
            res += "<a href=\"?toggle=" + s.Name + "\">[on]</a>"
        else:
            res += "<a href=\"?toggle=" + s.Name + "\">[off]</a>"
            
        res += "</li>\n"
    
    res += "</ul><br><br>"
    res += "Server started on: " + serverStartTime + ", last init on: " + serverLastInit
    
    return res



if __name__ == '__main__':
    loadConfig()
    setSchedule()
    startServer()
    botapp = bottle.app()
    server = WSGIServer((myAddress, int(myPort)), botapp)
#    server = WSGIServer(("10.0.1.223", int(myPort)), botapp , handler_class=WebSocketHandler)
    
    def shutdown():
        print('Shutting down ...')
        GPIO.cleanup()
        server.stop(timeout=5)
        exit(signal.SIGTERM)
        
    sig(signal.SIGTERM, shutdown)
    sig(signal.SIGINT, shutdown)
    
    server.serve_forever()

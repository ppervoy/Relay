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
import requests
from bottle import get, request, route, static_file, auth_basic
from gevent.pywsgi import WSGIServer
# from geventwebsocket.handler import WebSocketHandler
import time
from astral import Astral
from termcolor import colored
import RPi.GPIO as GPIO
from passlib.hash import sha256_crypt

configFile = "Relay.ini"
myCity = ""
myDepression = ""
myAddress = ""
myPort = ""
myAdmin = ""
myPasswd = ""
mySwitches = list()
serverStartTime = "1970/01/01 00:00"
serverLastInit = "1970/01/01 00:00"
plan = ""
iftttKey = ""



class Switch:
    Name = ""
    GPIOchannel = 0
    Type = "Sun"
    Status = False
    timeOn = "00:00"
    timeOff = "00:01"
    imgTop = "0px"
    imgLeft = "0px"
        
    def jobRelayOn(self):
        # print(colored("{} turned on {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'green'))
        self.Status = True
        GPIO.output(int(self.GPIOchannel), GPIO.HIGH)
        logging.info("+++ [%s] turned on %s (%s)", self.Name, self.GPIOchannel, self.Type)

    def jobRelayOff(self):
        # print(colored("{} turned off {}, type {}".format(self.Name, self.GPIOchannel, self.Type), 'red'))
        self.Status = False
        GPIO.output(int(self.GPIOchannel), GPIO.LOW)
        logging.info("--- [%s] turned off %s (%s)", self.Name, self.GPIOchannel, self.Type)
    
    def Start(self):
        # print(colored("Schedule \"{}\" started using {} on {}, off {}".format(self.Name, self.GPIOchannel, self.timeOn, self.timeOff), "blue"))
        schedule.every().day.at(str(self.timeOn)).do(self.jobRelayOn).tag(self.Name)
        schedule.every().day.at(str(self.timeOff)).do(self.jobRelayOff).tag(self.Name)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(int(self.GPIOchannel), GPIO.OUT)
        logging.info("^^^ Schedule [%s] started using %s on %s, off %s", self.Name, self.GPIOchannel, self.timeOn, self.timeOff)        
        
    def Stop(self):
        # print(colored("Schdeule \"{}\" stopped".format(self.Name), "blue"))
        schedule.clear(self.Name)
        logging.info("Schdeule [%s] stopped", self.Name)



def crc(fileName):
    prev = 0
    
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return "%X"%(prev & 0xFFFFFFFF)



configCRC = crc(configFile)



def loadConfig(file = configFile):
    config = configparser.RawConfigParser()
    config.read(file)
    logging.debug("*** Loading config file from %s ***", file)

    for e in config.sections():
        if e == "Global":
            global myCity
            global myDepression
            global myAddress            
            global myPort            
            global plan            
            global myAdmin            
            global myPasswd
            global iftttKey

            myCity = config["Global"]["City"]
            myDepression = config["Global"]["Depression"]
            myAddress = config["Global"]["Address"]
            myPort = config["Global"]["Port"]
            plan = config["Global"]["Plan"]
            myAdmin = config["Global"]["user"]
            myPasswd = config["Global"]["passwd"]
            iftttKey = config["Global"]["iftttKey"]

            logging.debug("Loaded global settings. City: %s, Depression: %s, web: %s@%s:%s Notifications key: %s", myCity, myDepression, myAdmin, myAddress, myPort, iftttKey)
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
                    s.timeOff = value
                elif name=="imgtop":
                    s.imgTop = value
                elif name=="imgleft":
                    s.imgLeft = value

            logging.debug("Loaded [%s] Type: %s, Channel: %s, TimeON: %s, TimeOFF: %s, X: %s, Y: %s", s.Name, s.Type, s.GPIOchannel, s.timeOn, s.timeOff, s.imgLeft, s.imgTop)

            mySwitches.append(s)
    
    a = Astral()
    a.solar_depression = myDepression
    city = a[myCity]
    
    sun = city.sun(date=datetime.date(datetime.datetime.today().year, datetime.datetime.today().month, datetime.datetime.today().day), local=True)
    duskh = str(sun['dusk'])[11:13]
    duskm = str(sun['dusk'])[14:16]
    dusk = duskh + ":" + duskm

    logging.debug("%s dusk in %s today is %s", myDepression, myCity, dusk)
    
    dawnh = str(sun['dawn'])[11:13]
    dawnm = str(sun['dawn'])[14:16]
    dawn =  dawnh + ":" + dawnm

    logging.debug("%s dawn in %s today is %s", myDepression, myCity, dawn)
    
    for s in mySwitches:
        if s.Type == "Sun":
            s.timeOn = dusk
            s.timeOff = dawn

        s.Start()
        
    GPIO.setmode(GPIO.BCM)
    now = datetime.datetime.now()
    
    global serverLastInit
    serverLastInit = now.strftime("%Y/%m/%d %H:%M:%S")

    logging.debug("*** Initialization is complete ***")
    requests.post("https://maker.ifttt.com/trigger/notify/with/key/" + iftttKey, params={"value1":"none","value2":"none","value3":"none"})


def jobUpdateAstral():
    a = Astral()
    a.solar_depression = myDepression
    city = a[myCity]
    
    sun = city.sun(date=datetime.date(datetime.datetime.today().year, datetime.datetime.today().month, datetime.datetime.today().day), local=True)
    duskh = str(sun['dusk'])[11:13]
    duskm = str(sun['dusk'])[14:16]
    dusk = duskh + ":" + duskm

    logging.debug("New %s dusk in %s is set to %s", myDepression, myCity, dawn)
    
    dawnh = str(sun['dawn'])[11:13]
    dawnm = str(sun['dawn'])[14:16]
    dawn =  dawnh + ":" + dawnm

    logging.debug("New %s dawn in %s is set to %s", myDepression, myCity, dawn)
    
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
        logging.debug("Configuration unchaged")
    else:
        logging.info("Configuration chaged! Reloading...")
        for s in mySwitches:
            s.Stop()
            del s
        mySwitches *= 0
        
        loadConfig()
        configCRC = crc(configFile)



def setSchedule():
    schedule.every(60).seconds.do(jobCheckConfig)
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



def isAuthUser(user, passwd):
    global myAdmin
    global myPasswd
    if user == myAdmin and passwd == myPasswd:
        from_ip = request.environ.get('REMOTE_ADDR')
        logging.info("Successful login from %s", from_ip)
        return True
    else:
        logging.warning("Failed login from %s", request.environ.get('REMOTE_ADDR'))
        logging.debug("L: %s, P: %s", user, passwd)
        logging.debug("Client: %s", request.environ.get('HTTP_USER_AGENT'))
        return False



@get('/<filename>')
def img(filename):
    return static_file(filename, root="/home/pi/Relay/img")

@get('/')
@auth_basic(isAuthUser)
def app():
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
    
    global plan
    
    res = "<html>\n<head>\n<title>WebRelay</title>\n</head>\n\n\n<body>\n"
    res += "<img src=\"" + plan + "\"/>\n"
    
    for s in mySwitches:
        
        if s.Status:
            res += "<a href=\"?toggle=" + s.Name + "\"><img src=\"on.png\" style=\"position: absolute; top: " + s.imgTop + "; left: " + s.imgLeft + "\" title=\"" + s.Name + " (triggered by " + s.Type + ", on: " + s.timeOn + " off: " + s.timeOff + ")\"/></a>"
        else:
            res += "<a href=\"?toggle=" + s.Name + "\"><img src=\"off.png\" style=\"position: absolute; top: " + s.imgTop + "; left: " + s.imgLeft + "\" title=\"" +s.Name + " (triggered by " + s.Type + ", on: " + s.timeOn + " off: " + s.timeOff  + ")\"/></a>"
            
    res += "<br>\n<br>\nServer started on: " + serverStartTime + ", last init on: " + serverLastInit
    res += "</body>\n</html>\n"
    
    return res



if __name__ == '__main__':
    logging.basicConfig(filename="WebRelay.log", format='%(asctime)s - %(message)s', level=logging.DEBUG, datefmt='%y/%m/%d %H:%M:%S')
    loadConfig()
    setSchedule()
    startServer()
    botapp = bottle.app()
    server = WSGIServer((myAddress, int(myPort)), botapp)
    
    def shutdown():
        logging.info("Shutting down...")
        GPIO.cleanup()
        server.stop(timeout=5)
        exit(signal.SIGTERM)
        
    sig(signal.SIGTERM, shutdown)
    sig(signal.SIGINT, shutdown)
    
    server.serve_forever()
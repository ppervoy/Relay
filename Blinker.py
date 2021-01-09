#!/usr/bin/env python3
import time, sys, datetime, RPi.GPIO as GPIO
    
if __name__ == '__main__':
    try:
    	GPIOchannel = 21
    	args = sys.argv[1:]
        GPIOchannel = int(args[0])
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIOchannel, GPIO.OUT)
        
        while True:
            GPIO.output(int(GPIOchannel), GPIO.LOW)
            sys.stdout.write("-")
            sys.stdout.flush() 
            time.sleep(0.35)
            GPIO.output(int(GPIOchannel), GPIO.HIGH)
            sys.stdout.write("\b")
            sys.stdout.write("+")
            sys.stdout.flush()
            sys.stdout.write("\b")
            time.sleep(0.35)
    except KeyboardInterrupt:
        GPIO.cleanup()
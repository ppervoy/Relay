# Relay
Raspberry Pi relay timed control is very handy for controlling growlights, watering plants etc.

# .ini file structure
```
[Global]
City=<your city>
Depression=civil
Address=<address to run web server on>
Port=<webserver port>
Plan=<your plan in .jpg located in img>
user=<user to login to webserver>
passwd=<user's password>
iftttKey=<IFTTT key to communicate with the service>


[<switch name>]
Type={Sun|Time|Manual}
TimeOn=<if type is Time add time to turn on>
TimeOff=<same here>
GPIOchannel=<GPIO to activate>
ImgTop=<location of switch on plan in px>
ImgLeft=<location of switch on plan in px>
```

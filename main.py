from bluepy import btle
import requests
import time
import datetime
from dataclasses import dataclass

#posturl = "XXXXXXXX"
posturl = "XXXXXX"
proxy_dict = {
    "http": "http://proxy.uec.ac.jp:8080/",
    "https": "http://proxy.uec.ac.jp:8080/"
}
takoyakisan_apiurl = "YYYYYYYYYYYYYYYY"
gotti_apiurl = "ZZZZZZZZZZZ"

scanner = btle.Scanner(0)
avgnop = 0
oldAvgnop = 0
listOfnop = [0] * 10*3*20 #number of people (last 10 * 3 * 20 times, approximately 10min)
lastposted = 0
lastupdated = 0

@dataclass
class User:
    rpid:int = 0
    remainingtime:int = 20 # 60s = scantime(3s) * 20 times

    def inctime(self):
        self.remainingtime += 1
        #print("remainingtime  "+str(self.remainingtime))
    def dectime(self):
        self.remainingtime -= 1
        #print("remainingtime  "+str(self.remainingtime))
    def rsttime(self):
        self.remainingtime = 20
        #print("remainingtime  "+str(self.remainingtime))
    def discovered(self):
        self.remainingtime = 20
        #print("remainingtime  "+str(self.remainingtime))
    def setrpid(self,rpid):
        self.rpid = rpid
    def getrpid(self):
        return self.rpid

@dataclass
class Device():
    uuid:int = 0
    rpid:int = 0
    rssi:int = 0

    def setuuid(self, uuid=0):
        self.uuid = uuid
    def setrpid(self, rpid=0):
        self.rpid = rpid
    def setrssi(self, rssi=0):
        self.rssi = rssi
    def getrpid(self): #15分おきにかわるID
        return self.rpid
    def getuuid(self): #COCOA特有のUUID
        return self.uuid
    def getrssi(self): #電波強度
        return self.rssi

joinedusers = dict()
queuedusers = dict()
while True:
    devs = scanner.scan(3.0) # block 3 seconds for scan
    devices = dict()
    for dev in devs:
        device = Device()
        for (adTypeCode, description, valueText) in dev.getScanData():
            if adTypeCode == 3:
                device.setuuid(valueText) #  == "0000fd6f-0000-1000-8000-00805f9b34fb"
                if valueText == "0000fd6f-0000-1000-8000-00805f9b34fb":
                    #print("!----!")
                    print(time.time(),dev.rssi,dev.getScanData())
                    #print("!----!")
            if adTypeCode == 22:
                device.setrpid(valueText)
                device.setrssi(dev.rssi)
        if device.getuuid() != 0 and device.getrpid() != 0:
            devices[device.getrpid()] = device

    #update exist data
    for k in sorted(devices.keys()):
        print(time.time(),devices[k].getrpid(),devices[k].getrssi())
        print("-----------------------------------------------------")

    for k in (joinedusers.keys() & devices.keys()): #キーの積集合
        joinedusers[k].rsttime()

    for k in (joinedusers.keys() - devices.keys()): #キーの差集合
        v=joinedusers[k]
        v.inctime()
        if v.remainingtime == 20*1+20:
            joinedusers.pop(k)

    for k in (queuedusers.keys() & devices.keys()): #キーの積集合
        v=queuedusers[k]
        v.dectime()
        if v.remainingtime == 0:
            v.rsttime()
            joinedusers[k] = v
            queuedusers.pop(k)

    for k in (queuedusers.keys() - devices.keys()): #キーの差集合
        v=queuedusers[k]
        v.inctime()
        if v.remainingtime == 20*1+20:
            queuedusers.pop(k)

    #add new data
    for k in (devices.keys() - queuedusers.keys() - joinedusers.keys()):
        queuedusers[k] = User(devices[k].getrpid())

    #rotate and replace oldest nop
    listOfnop = listOfnop[1:] + [len(joinedusers)]
    l = 0
    for i in listOfnop:
        l += i
    print(len(listOfnop))
    avgnop = round(round(l/len(listOfnop)))

    #nop = len(joinedusers)
    if time.time()-lastupdated >= 300:
        lastupdated = time.time()
        r = requests.get(takoyakisan_apiurl+str(avgnop),proxies=proxy_dict)
        ie = requests.get(gotti_apiurl, proxies=proxy_dict)
        if r.json()["status"]!="ok":
            payload1 = {"content:" "APIサーバへのアクセスに失敗"}
            requests.post(posturl, json=payload1,proxies=proxy_dict)
        print("updated")

    if time.time()-lastposted >= 300:
        if len(queuedusers) == 0 and avgnop != oldAvgnop:
            lastposted = time.time()
            now = datetime.datetime.fromtimestamp(time.time())
            payload = {"content": f"[{now.strftime('%H:%M:%S')}] 部室にいるCOCOA利用者:{oldAvgnop}→{avgnop}"}
            requests.post(posturl, json=payload, proxies=proxy_dict)
            oldAvgnop = avgnop

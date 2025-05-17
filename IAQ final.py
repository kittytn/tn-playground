import pika
import json
import time
import random
import uuid
from datetime import datetime
#RabbitMQ connection parameters
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'iaq_sensor_data'
#Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME)

# Generate 15 virtual sensors with unique IDs(IAQ15ตัว)
sensor_ids = []
for i in range(15):
    if i < 10:
        n = "UUID0"+str(i)
        sensor_ids.append(n)
    else:
        n = "UUID"+str(i)
        sensor_ids.append(n)
        
receive = {} #สำหรับจัดการข้อมูล ข้อมูลใหม่ทุก 15 วิ

#Generate Data
#**************************************************************
#Normal Situation
def generate_sensor_data(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(20.0, 30.0), 2),       # in °C
        "humidity": round(random.uniform(30.0, 70.0), 2),          # in %RH
        "co2": random.randint(400, 1200)                           # in ppm
    }
#ERROR1 SIMULATE
def generate_sensor_data1(sensor_id): 
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": 25.0,       # in °C
        "humidity": 70.0,          # in %RH
        "co2": 200                 # in ppm
    }
#ERROR2 SIMULATE
def generate_sensor_data2(sensor_id): 
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(-100, 120), 2),       # in °C
        "humidity":round(random.uniform(0, 200), 2),# in %RH
        "co2":random.randint(800, 1200)              # in ppm
    }
#ERROR3 SIMULATE
def generate_sensor_data3(sensor_id): 
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(20.0, 30.0), 2),       # in °C
        "humidity": round(random.uniform(30.0, 70.0), 2),          # in %RH
        "co2":random.randint(1200,1400)              # in ppm
    }
#**************************************************************
#===============================================================
#จัดการข้อมูล ใส่receiveทุก15วิ
def get_data_function(message):
    message = message[1:len(message)-1] #ตัดปีกกา
    message = message.split(",")
    UUID = message[0].split(": ")[1]
    UUID = UUID[1:len(UUID)-1]
    receive[UUID] = {}
    for i in range(1,len(message)):
        message[i] = message[i][1:len(message[i])] #*
        word = message[i].split(": ")
        receive[UUID][word[0][1:len(word[0])-1]] = word[1]
    return receive
# recieve=[UUID:{time:data,temp:data,humidity:data,co2:data}]

#**********************************************************************
#======================================================================
#patameter ไม่ต้องเอาใส่loop
#ERROR1
count1 = {}
detect = {}
#ERROR3
count3 = {}
#for alert notification
alert = []
for UUID in sensor_ids:
    count1[UUID] = 0
    count3[UUID] = 0
    
#function====================================================================
#============================================================================
def sensor_error1(detect):
    checked12 = [] #เก็บผลการcheckของทุกUUIDใน1set ว่าข้อมูลซ้ำกับที่ส่งมาก่อนหน้าไหม
#====เริ่มchecked11ข้อมูลในแต่ละsetว่าซ้ำกับเซทก่อนหน้าไหม
    for UUID in receive.keys():
        checked11 = [] #เปลี่ยนตามแต่ละ UUID
        checked11.append(float(receive[UUID]["temperature"]))
        checked11.append(float(receive[UUID]["humidity"]))
        checked11.append(float(receive[UUID]["co2"]))
        if detect[UUID] == checked11 : #ถ้าเหมือน->บันทึกลงในchecked12
            checked12.append(True)
        else:
            detect[UUID] = checked11 #ถ้าไม่เหมือน->เปลี่ยนdetect(ที่เอาไว้ตรวจ)เปนอันล่าสุด
            checked12.append(False)
    #checked12 = [T,T,T,F,T..]
    return checked12

def sensor_error2():
    detected = []
    detect = {} #เอาไว้บอกตัวผิด
    checked21 = [100,100,10000] #max
    checked22 = [-100,0,0] #min
    checked23 = ["temperature","humidity","co2"]
    for UUID in receive.keys():
        detect[UUID] = []
        detect[UUID].append(receive[UUID]["temperature"])
        detect[UUID].append(receive[UUID]["humidity"])
        detect[UUID].append(receive[UUID]["co2"])
    for UUID in detect.keys():
        for i in range(3):
            if float(detect[UUID][i]) >= checked21[i] or float(detect[UUID][i]) < checked22[i]:
                detected.append(["Invalid",checked23[i].upper(),"value from sensor:",UUID])
    return detected

def sensor_error3(): #ทำงานทุก15วินาที
    #ใช้ทุกerror============================================
    detect = {}
    check31 = []
    for UUID in receive.keys():
        detect[UUID] = []
        detect[UUID].append(float(receive[UUID]["temperature"]))
        detect[UUID].append(float(receive[UUID]["humidity"]))
        detect[UUID].append(float(receive[UUID]["co2"]))
    #==================================================
    #ตรวจแต่ละตัว ทุก15วิ
    for UUID in detect.keys():
        if detect[UUID][2] > 1000:
            check31.append(True)
    return check31
#============================================================================
#============================================================================
#Detection Integration
def error_detection():
    alert = []
    e1 = []
    e3 = []
    checked12 = sensor_error1(detect)
    for i in range(len(checked12)):
        if checked12[i] == True:
            count1[sensor_ids[i]] += 1
        else:
            count1[sensor_ids[i]] = 0
    for k in count1.keys():
        if count1[k] >= 40 and k not in e1:
                e1.append(k)
    if len(e1) != 0:
        s1 = ["Error Type 1:",e1]
        alert.append(s1)
        
    error2 = sensor_error2()
    for word in error2:
        s2 = word[0]+" "+word[1]+" "+word[2]+" "+word[3]
        alert.append([s2])
    checked31 = sensor_error3()
    for i in range(len(checked31)):
        if checked31[i] == True:
            count3[sensor_ids[i]] += 1
            if count3[sensor_ids[i]] >= 80 and sensor_ids[i] not in e3:
                e3.append(sensor_ids[i])
        else:
            count3[sensor_ids[i]] = 0
    if len(e3) != 0:
        s3 = ["Error Type 3:",e3]
        alert.append(s3)
    return alert

#=================================================================
try:
    while True:
        for UUID in sensor_ids:
            data = generate_sensor_data2(UUID)#*
            message = json.dumps(data)
            channel.basic_publish(exchange='',
                                  routing_key=QUEUE_NAME,
                                  body=message)
            receive = get_data_function(message) #สร้างreceive เอาไว้จัดการข้อมูลต่อ
            
        #สำหรับerror1
        if detect == {}:
            for UUID in receive.keys():
                detect[UUID] = []
                detect[UUID].append(float(receive[UUID]["temperature"]))
                detect[UUID].append(float(receive[UUID]["humidity"]))
                detect[UUID].append(float(receive[UUID]["co2"]))
        alerts = error_detection()
        if len(alerts) != 0:
            for alert in alerts:
                alert_message = " ".join(str(item) for item in alert)
                print(alert_message)

        else:
            print("✅ สถานะปกติ", icon="✅")
#         for word in alert:
#             print(word)
        time.sleep(15)
except KeyboardInterrupt: #กดctrl+c
    print("Simulation stopped.")
finally:
    connection.close()
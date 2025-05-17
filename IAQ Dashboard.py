import streamlit as st
import pandas as pd
import numpy as np
import pika
import json
import time
import random
import uuid
from datetime import datetime
import altair as alt
from datetime import timedelta, timezone

# RabbitMQ connection parameters
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'iaq_sensor_data'

# Connect to RabbitMQ
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
        
receive = {}  # สำหรับจัดการข้อมูล ข้อมูลใหม่ทุก 15 วิ

# Generate Data
# **************************************************************
# Normal Situation
def generate_sensor_data(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(20.0, 30.0), 2),
        "humidity": round(random.uniform(30.0, 70.0), 2),
        "co2": random.randint(400, 1200)
    }

# ERROR1 SIMULATE
def generate_sensor_data1(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": 25.0,
        "humidity": 70.0,
        "co2": 200
    }

# ERROR2 SIMULATE
def generate_sensor_data2(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(-100, 120), 2),
        "humidity": round(random.uniform(0, 200), 2),
        "co2": random.randint(800, 1200)
    }

# ERROR3 SIMULATE
def generate_sensor_data3(sensor_id):
    return {
        "sensor_id": sensor_id,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "temperature": round(random.uniform(20.0, 30.0), 2),
        "humidity": round(random.uniform(30.0, 70.0), 2),
        "co2": random.randint(1200, 1400)
    }

# **************************************************************
# จัดการข้อมูล ใส่receiveทุก15วิ
def get_data_function(message):
    message = message[1:len(message)-1]
    message = message.split(",")
    UUID = message[0].split(": ")[1]
    UUID = UUID[1:len(UUID)-1]
    receive[UUID] = {}
    for i in range(1, len(message)):
        message[i] = message[i][1:len(message[i])]
        word = message[i].split(": ")
        receive[UUID][word[0][1:len(word[0])-1]] = word[1]
    return receive

# parameter ไม่ต้องเอาใส่loop
count1 = {}
detect = {}
count3 = {}
alert = []
for UUID in sensor_ids:
    count1[UUID] = 0
    count3[UUID] = 0

def sensor_error1(detect):
    checked12 = []
    for UUID in receive.keys():
        checked11 = []
        checked11.append(float(receive[UUID]["temperature"]))
        checked11.append(float(receive[UUID]["humidity"]))
        checked11.append(float(receive[UUID]["co2"]))
        if detect[UUID] == checked11:
            checked12.append(True)
        else:
            detect[UUID] = checked11
            checked12.append(False)
    return checked12

def sensor_error2():
    detected = []
    detect = {}
    checked21 = [100, 100, 10000] #max
    checked22 = [-100, 0, 0] #min
    checked23 = ["temperature", "humidity", "co2"]
    for UUID in receive.keys():
        detect[UUID] = []
        detect[UUID].append(receive[UUID]["temperature"])
        detect[UUID].append(receive[UUID]["humidity"])
        detect[UUID].append(receive[UUID]["co2"])
    for UUID in detect.keys():
        for i in range(3):
            if float(detect[UUID][i]) >= checked21[i] or float(detect[UUID][i]) < checked22[i]:
                detected.append(["Invalid", checked23[i].upper(), "value from sensor:", UUID])
    return detected

def sensor_error3():
    detect = {}
    check31 = []
    for UUID in receive.keys():
        detect[UUID] = []
        detect[UUID].append(float(receive[UUID]["temperature"]))
        detect[UUID].append(float(receive[UUID]["humidity"]))
        detect[UUID].append(float(receive[UUID]["co2"]))
    for UUID in detect.keys():
        if detect[UUID][2] > 1000:
            check31.append(True)
    return check31

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

# ตั้งชื่อหน้าDashboard
st.set_page_config(page_title="Real-Time IAQ Dashboard", layout="wide")
st.title("📡 Real-Time IAQ Sensor Dashboard")
st.markdown("อัปเดตข้อมูลคุณภาพอากาศภายในอาคารแบบเรียลไทม์")

# สร้างตัวเก็บข้อมูลเริ่มต้น
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["UUID", "timestamp", "temperature", "humidity", "co2"])

# สร้างกราฟ placeholder สำหรับเก็บข้อมูลที่อัปเดตตลอดเวลา
placeholder = st.empty()
# เก็บแจ้งเตือนผิดปกติ
alert_placeholder = st.empty()
#=========================================================================
#time range
st.sidebar.header("⏱️ กำหนดช่วงเวลาแสดงข้อมูล")
time_range_min = st.sidebar.slider("แสดงข้อมูลย้อนหลัง (นาที)", min_value=1, max_value=60, value=10, step=1)
# multi selected -> dropdown ให้ผู้ใช้เลือก UUID ที่ต้องการดูบนกราฟ
sensor_options = sensor_ids
st.sidebar.header('Select Sensor(s)')
#selected_UUID = st.sidebar.selectbox("UUID:",options=sensor_options)
selected_UUIDs = st.sidebar.multiselect("Choose",options=sensor_options, default=sensor_ids)
#notification
st.sidebar.header('Notification(s)')
notification_area = st.sidebar.empty()
#===================================================================================
try:
    while True:
        sidebar_alert_placeholder = st.sidebar.empty()
        for UUID in sensor_ids:
            data = generate_sensor_data(UUID)
            message = json.dumps(data)
            channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=message)
            receive = get_data_function(message)
            receive[UUID]["UUID"] = UUID
            iso_str = receive[UUID]["timestamp"]
            time_cleaned = iso_str.strip('"').replace("Z", "+00:00")
            receive[UUID]["timestamp"] = datetime.fromisoformat(time_cleaned)
            st.session_state.data = pd.concat([
                st.session_state.data,
                pd.DataFrame([receive[UUID]])
            ]).tail(1000)

        if detect == {}:
            for UUID in receive.keys():
                detect[UUID] = []
                detect[UUID].append(float(receive[UUID]["temperature"]))
                detect[UUID].append(float(receive[UUID]["humidity"]))
                detect[UUID].append(float(receive[UUID]["co2"]))     
        #sidebar multiselected======
        filtered_data = st.session_state.data[st.session_state.data["UUID"].isin(selected_UUIDs)].copy()
        filtered_data["UUID"] = filtered_data["UUID"].astype(str)
        #time rangeจากslider
        # แปลง timestamp เป็น timezone-aware
        filtered_data["timestamp"] = pd.to_datetime(filtered_data["timestamp"], utc=True)
        now = datetime.now(timezone.utc)  # แก้ตรงนี้ให้เป็น timezone-aware
        time_threshold = now - timedelta(minutes=time_range_min)
        filtered_data = filtered_data[filtered_data["timestamp"] >= time_threshold]
        # แปลง timestamp เป็น string format เวลา
        filtered_data['time_str'] = filtered_data['timestamp'].dt.strftime('%H:%M:%S')
        #==================================
        with placeholder.container():
            st.subheader("Temperature (°C)")
            chart_temp = alt.Chart(filtered_data).mark_line().encode(
                x=alt.X('time_str:O', title='Time (hh:mm:ss)'),
                y=alt.Y('temperature:Q', title='Temperature (°C)'),
                color=alt.Color('UUID:N', title='Sensor ID'),
                tooltip=['time_str:N', 'temperature:Q', 'UUID']
            ).properties(width='container', height=400).interactive()
            st.altair_chart(chart_temp, use_container_width=True)

            st.subheader("Humidity (%RH)")
            chart_hum = alt.Chart(filtered_data).mark_line().encode(
                x=alt.X('time_str:O', title='Time (hh:mm:ss)'),
                y=alt.Y('humidity:Q', title='Humidity (%RH)'),
                color=alt.Color('UUID:N', title='Sensor ID'),
                tooltip=['time_str:N', 'humidity:Q', 'UUID']
            ).properties(width='container', height=400).interactive()
            st.altair_chart(chart_hum, use_container_width=True)

            st.subheader("CO2 (ppm)")
            chart_co2 = alt.Chart(filtered_data).mark_line().encode(
                x=alt.X('time_str:O', title='Time (hh:mm:ss)'),
                y=alt.Y('co2:Q', title='CO2 (ppm)'),
                color=alt.Color('UUID:N', title='Sensor ID'),
                tooltip=['time_str:N', 'co2:Q', 'UUID']
            ).properties(width='container', height=400).interactive()
            st.altair_chart(chart_co2, use_container_width=True)

            st.dataframe(st.session_state.data.tail(15), use_container_width=True)
# =========================================
# ⏱ เก็บข้อมูลใหม่ และแสดงการแจ้งเตือนล่าสุดเท่านั้น
        alerts = error_detection()
        with notification_area.container():
            st.header("🔍 การแจ้งเตือนเซนเซอร์")

            if len(alerts) != 0:
                for alert in reversed(alerts):
                    alert_message = " ".join(str(item) for item in alert)
                    st.error(f"🚨 {alert_message}")
                    st.markdown("---")
            else:
                st.success("✅ สถานะปกติ ไม่มีความผิดปกติในระบบ")
#========================================
        time.sleep(15)

except KeyboardInterrupt:
    print("Simulation stopped.")
finally:
    connection.close()
#ใช้ python -m streamlit run "IAQ Dashboard.py" ใน terminal เพื่อรัน
from sre_constants import AT_BOUNDARY
import tkinter as tk
import socket
import struct
import logging
from threading import Thread
import time

import os
from functools import partial
import random
from concurrent.futures import * 
from datetime import datetime
import glob
from datetime import datetime, timedelta
import threading

import shutil
import regex
import datetime
import binascii


logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] %(threadName)s: %(message)s')

serverIp = '192.168.1.42'

gatewayIp = '192.168.1.1'

prefixIp = '192.168.1.'

cidr = '192.168.1.0/24'

devices=[]
devicesAlive=[]

uiBrakes=[]
uiAxles=[]
uiTurnings=[]
uiUps=[]

unpackerLength = struct.Struct('I')
int_size = struct.calcsize("I")

pwmValue = 0

TIME_BETWEEN_ASK_UPS = 3

AXILE_OFFSET_11 = 0
AXILE_OFFSET_12 = 4
AXILE_OFFSET_13 = 2
AXILE_OFFSET_14 = 1

executor = ThreadPoolExecutor()

bControlClientisDead = False

def SendDataAndGetResponse(sock, data):
    #send
    packerContent = struct.Struct('I'+ str(len(data)) + 'B')
    packedContent = packerContent.pack(len(data), *data)

    try:
        sock.send(packedContent)
    except socket.error as msg:
        return []
    
    '''
    #receive response
    try:
        data1 = sock.recv(unpackerLength.size)
    except socket.error as msg:
        return []

    #print('received "%s"' % binascii.hexlify(data1))
    if(len(data1) >=4):
        unpacked_length = unpackerLength.unpack(data1)[0]
        #print('unpacked length:', unpacked_length)

        try:
            data2 = sock.recv(unpacked_length)
        except socket.error as msg:
            return []

        #print('received "%s"' % binascii.hexlify(data2))
        unpackerContent = struct.Struct(str(unpacked_length) + 'B')
        unpacked_content = unpackerContent.unpack(data2)
        #print('Got message:', unpacked_content)
        return unpacked_content
    '''
    

def RemoveDeviceWithAliveSock(sock):
    devicesToRemove = [device for device in devicesAlive if device['sock'] == sock]
    if len(devicesToRemove) != 0:
        deviceToRemove = devicesToRemove[0]
        devicesAlive.remove(deviceToRemove)
    
        devicesToRemove1 = [device for device in devices if device['id'] == deviceToRemove['id']]
        if len(devicesToRemove1) != 0:
            deviceToRemove1 = devicesToRemove1[0]

        devices.remove(deviceToRemove1)
        
        UpdateUi(id=deviceToRemove['id'], ip='null')

def LoopReceiveAliveAignalAndResponse(sock):
    while True:
        #receive
        try:
            sock.settimeout(10)
            data1 = sock.recv(unpackerLength.size)
        except socket.error as msg:
            print('[LoopReceiveAliveAignalAndResponse] Caught exception socket.error : ', msg)
            RemoveDeviceWithAliveSock(sock)
            break
        #print('received "%s"' % binascii.hexlify(data1))
        if(len(data1) >=4):
            unpacked_length = unpackerLength.unpack(data1)[0]
            #print('unpacked length:', unpacked_length)
            try:
                data2 = sock.recv(unpacked_length)
            except socket.error as msg:
                print('[LoopReceiveAliveAignalAndResponse] Caught exception socket.error : ', msg)
                RemoveDeviceWithAliveSock(sock)
                break
            #print('received "%s"' % binascii.hexlify(data2))
            unpackerContent = struct.Struct(str(unpacked_length) + 'B')
            unpacked_content = unpackerContent.unpack(data2)
            #print('Got message:', unpacked_content)

        if len(unpacked_content) > 3 and unpacked_content[0] == 0x42 and unpacked_content[1] == 0x42 and unpacked_content[2] == 0x42:
            #send
            data = (0x43, 0x43, 0x43, 0x43)
            packerContent = struct.Struct('I'+ str(len(data)) + 'B')
            packedContent = packerContent.pack(len(data), *data)
            try:
                sock.send(packedContent)
            except socket.error as msg:
                print('[LoopReceiveAliveAignalAndResponse] Caught exception socket.error : ', msg)
                RemoveDeviceWithAliveSock(sock)
                break

def LoopHandleControlCommand(sock):
    while True:
        #receive
        try:
            data1 = sock.recv(unpackerLength.size)
        except socket.error as msg:
            print('[LoopHandleControlCommand] Caught exception socket.error : ', msg)
            break
        
        if(len(data1) >=4):
            unpacked_length = unpackerLength.unpack(data1)[0]
            #print('unpacked length:', unpacked_length)
            try:
                data2 = sock.recv(unpacked_length)
            except socket.error as msg:
                print('[LoopHandleControlCommand] Caught exception socket.error : ', msg)
                break
            #print('received "%s"' % binascii.hexlify(data2))
            unpackerContent = struct.Struct(str(unpacked_length) + 'B')
            unpacked_content = unpackerContent.unpack(data2)
            HandleControlCommand(unpacked_content)

            '''
            #send
            data = (0x43, 0x43, 0x43, 0x43)
            packerContent = struct.Struct('I'+ str(len(data)) + 'B')
            packedContent = packerContent.pack(len(data), *data)
            try:
                sock.send(packedContent)
            except socket.error as msg:
                print('Caught exception socket.error : ', msg)
            '''
            


def SendCommandBreak(sock):
    sendOutData = (0x69, 0x74, 0x72, 0x69, 0x00, 0x01, 0x01, 0x00, 0x02, 0x00, 0x00)
    receivedData = SendDataAndGetResponse(sock, data=sendOutData)
    print('Break, received data =', receivedData)
    return receivedData

def SendCommandGetUpsInfo(sock):
    sendOutData = (0x69, 0x74, 0x72, 0x69, 0x00, 0x02, 0x02, 0x00, 0x00)
    receivedData = SendDataAndGetResponse(sock, data=sendOutData)
    print('Ups, received data =', receivedData)
    return receivedData

def LoopSendCommandGetUpsInfo():
    #print('LoopSendCommandGetUpsInfo')
    while True:
        #print('device number =', len(devices))
        for device in devices:
            #print('testing device', device['id'])
            if device['id'] in range (21, 30):
                print('\nsend command UPS, device id=', device['id'])
                #Thread(target=sendCommandGetUpsInfo, args=device['sock'])
                time.sleep(TIME_BETWEEN_ASK_UPS-1 + random.random())
                receivedData = SendCommandGetUpsInfo(sock = device['sock'])
                print('received data = ', receivedData)

                if(receivedData is not None and len(receivedData) == 25):
                    volIn = struct.unpack('<f', bytes(receivedData[9:13]))[0]
                    print('volIn = %0.2f' % volIn)
                    ampIn = struct.unpack('<f', bytes(receivedData[13:17]))[0]
                    print('ampIn = %0.2f' % ampIn)
                    volOut = struct.unpack('<f', bytes(receivedData[17:21]))[0]
                    print('volOut = %0.2f' % volOut)
                    ampOut = struct.unpack('<f', bytes(receivedData[21:25]))[0]
                    print('ampOut = %0.2f' % ampOut)

                    UpdateUi(id=device['id'], ip=device['addr'][0], 
                            info0='%0.2f' % volIn,
                            info1='%0.2f' % ampIn,
                            info2='%0.2f' % volOut,
                            info3='%0.2f' % ampOut)
                else:
                    print('No ack from UPS module ID: ', device['id'])

def LoopHandleJoystickEvents():
    joystickProgram = Joystick()
    joystickProgram.init(GoForwardCommand, GoBackwardCommand, TurnLeftCommand, TurnRightCommand, BrakeAllCommand)
    joystickProgram.run()


def SendCommandSetAxleAndGetResponse(sock, runDirection = 0, brake = False, pwm = 0):
    sendOutData = [0x69, 0x74, 0x72, 0x69, 0x00, 0x04, 0x01, 0x00, 0x03]

    sendOutData.append(bytes([runDirection])[0])

    if brake:
        sendOutData.append(0x01)
    else:
        sendOutData.append(0x00)

    sendOutData.append(bytes([pwm])[0])
    #sendOutData.append(0x30)

    print('send axle command =', sendOutData)

    receivedData = SendDataAndGetResponse(sock, data=sendOutData)
    print('Axle, received data =', receivedData)
    return receivedData


def GetIpAddress():
    from subprocess import check_output
    ipAddr = check_output(['hostname', '--all-ip-addresses']).decode("utf-8")
    return ipAddr


def MakeSureGotLanIp():
    myIpAddr = GetIpAddress()
    print('Server IP = ', myIpAddr)

    #while not myIpAddr.startswith(prefixIp):
    while not myIpAddr.startswith(serverIp):
        time.sleep(2)
        myIpAddr = GetIpAddress()
        print('Waiting for IP, current IP is ', myIpAddr)
        
    #print('Set Server IP = ', myIpAddr)
    #os.system('netsh interface ip set dns name="Wi-Fi" static ' + gatewayIp)

def LoopGetConnectionFromADecice():
    portNumber = 10002
    unpackerLength = struct.Struct('I')

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server_address = ('', portNumber)
    server_address = ('0.0.0.0', portNumber)
    sock.bind(server_address)
    sock.listen(24)

    while True:
        #print('\nwaiting for a connection')
        connection, client_address = sock.accept()

        try:
            #receive
            data1 = connection.recv(unpackerLength.size)
            #print('received "%s"' % binascii.hexlify(data1))
            if(len(data1) >=4):
                unpacked_length = unpackerLength.unpack(data1)[0]
                #print('unpacked length:', unpacked_length)
                data2 = connection.recv(unpacked_length)
                #print('received "%s"' % binascii.hexlify(data2))
                unpackerContent = struct.Struct(str(unpacked_length) + 'B')
                unpacked_content = unpackerContent.unpack(data2)
                #print('Got message:', unpacked_content)
                
                #command: tell id 
                #print('command = ', unpacked_content[4], unpacked_content[5])
                if unpacked_content[4]==0 and unpacked_content[5]==3:
                    deviceId = unpacked_content[9]
                    print('got id = ', deviceId)
                    if deviceId != 0:
                        #add new device into delice list
                        newDevice = {'addr':client_address,'id':deviceId, 'sock':connection}
                    
                        for device in devices:
                            if device['id'] == deviceId:
                                devices.remove(device)
                                break

                        devices.append(newDevice)

                        print('\n------------------------------------------')
                        print('\t ID\t Address\t Socket')
                        for device in devices:
                            print('\t', device['id'], '\t',device['addr'], device['sock'])
                            UpdateUi(id=device['id'], ip=device['addr'][0])
                        print('------------------------------------------\n')

                        #send ID response
                        #print('response to \'tell ID\'')
                        data = (0x69, 0x74, 0x72, 0x69, 0x00, 0x03, 0x10, 0x00, 0x00)
                        packerContent = struct.Struct('I'+ str(len(data)) + 'B')
                        packedContent = packerContent.pack(len(data), *data)
                        connection.send(packedContent)
                        
                    else:
                        #send ID response
                        #print('response to \'tell ID\'')
                        data = (0x69, 0x74, 0x72, 0x69, 0x00, 0x03, 0x10, 0x00, 0x00)
                        packerContent = struct.Struct('I'+ str(len(data)) + 'B')
                        packedContent = packerContent.pack(len(data), *data)
                        connection.send(packedContent)



        finally:
            pass
            #connection.close()
      
def LoopGetAliveSignal():
    portNumber = 10003
    unpackerLength = struct.Struct('I')

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', portNumber)
    sock.bind(server_address)
    sock.listen(24)

    while True:
        #print('\nwaiting for a connection')
        connection, client_address = sock.accept()

        try:
            #receive
            data1 = connection.recv(unpackerLength.size)
            #print('received "%s"' % binascii.hexlify(data1))
            if(len(data1) >=4):
                unpacked_length = unpackerLength.unpack(data1)[0]
                #print('unpacked length:', unpacked_length)
                data2 = connection.recv(unpacked_length)
                #print('received "%s"' % binascii.hexlify(data2))
                unpackerContent = struct.Struct(str(unpacked_length) + 'B')
                unpacked_content = unpackerContent.unpack(data2)
                #print('Got message:', unpacked_content)
                
                #command: tell id 
                #print('command = ', unpacked_content[4], unpacked_content[5])
                if len(unpacked_content) >= 5 and unpacked_content[4]==0 and unpacked_content[5]==3:
                    deviceId = unpacked_content[9]
                    #print('got Alive id = ', deviceId)

                    if deviceId != 0:
                        #add new device into delice list
                        newDevice = {'addr':client_address,'id':deviceId, 'sock':connection}
                        devicesAlive.append(newDevice)

                    handler = Thread(target=LoopReceiveAliveAignalAndResponse, args=(connection,))
                    handler.start()

                    #send ID response
                    #print('response to \'tell ID\'')
                    data = (0x69, 0x74, 0x72, 0x69, 0x00, 0x03, 0x10, 0x00, 0x00)
                    packerContent = struct.Struct('I'+ str(len(data)) + 'B')
                    packedContent = packerContent.pack(len(data), *data)
                    connection.send(packedContent)
                
            else:
                print('ABNORMAL alive signal is received')

                
        finally:
            pass
            #connection.close()

def merge_files_and_build_txt(directory='/home/pi/', ext='.bin'):
    #===========MERGE============
    # Search for all files
    files = glob.glob(os.path.join(directory, '*' + ext))

    # Create a regex pattern to check filenames
    pattern = regex.compile(r'\d{17}' + regex.escape(ext) + r'$')

    # Filter out the files with the correct format
    filtered_files = [f for f in files if pattern.search(os.path.basename(f))]

    # If filtered_files is empty, return directly
    if not filtered_files:
        return

    # Parse filenames to time and sort
    sorted_files = sorted(filtered_files, key=lambda x: int(os.path.basename(x).split('.')[0]))

    # Initialize a list to store file groups
    file_groups = []
    current_group = [sorted_files[0]]

    # Iterate through each file, if the time gap exceeds 2 seconds then create a new group
    for i in range(1, len(sorted_files)):
        current_file = sorted_files[i]
        last_file = current_group[-1]
        current_time = datetime.datetime.strptime(os.path.basename(current_file)[:-4], '%Y%m%d%H%M%S%f')
        last_time = datetime.datetime.strptime(os.path.basename(last_file)[:-4], '%Y%m%d%H%M%S%f')

        if (current_time - last_time).total_seconds() > 4:
            file_groups.append(current_group)
            current_group = [current_file]
        else:
            current_group.append(current_file)

    # Append the last group
    file_groups.append(current_group)

    # Iterate through each group to merge files
    for group in file_groups:
        if len(group) > 1:
            # The file with the maximum timestamp in the group
            max_file = max(group, key=os.path.getctime)
            # Temporary file for merging
            temp_file_name = os.path.join(directory, 'temp' + ext)

            # Open the temporary file and write data
            with open(temp_file_name, 'wb') as outfile:
                for fname in sorted(group, key=os.path.getctime):  # Ensure that the files are merged in time order
                    with open(fname, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)

            # Rename the temporary file to the file with the maximum timestamp
            new_file_name = os.path.join(directory, os.path.basename(max_file))
            os.rename(temp_file_name, new_file_name)

            # Delete the original files
            for fname in group:
                if fname != max_file:  # Do not delete the file with the maximum timestamp
                    os.remove(fname)

    #========BUILD TXT===========
    pattern = regex.compile(r"\d{17}.bin$")

    for root, dirs, files in os.walk(directory):
        for file in files:
            if pattern.match(file):
                bin_file_path = os.path.join(root, file)
                with open(bin_file_path, "rb") as bin_file:
                    bin_content = bin_file.read()
                    hex_content = binascii.hexlify(bin_content).decode()
                    hex_content = " ".join([hex_content[i: i+2] for i in range(0, len(hex_content), 2)])

                    hex_content_lines = [hex_content[i: i+21*3-1] for i in range(0, len(hex_content), 21*3)]
                    hex_content_with_newlines = "\n".join(hex_content_lines)

                    txt_file_path = bin_file_path.replace(".bin", ".txt")
                    with open(txt_file_path, "w") as txt_file:
                        txt_file.write(hex_content_with_newlines)
    
    
current_client = None
current_connection = None

def handle_client(connection, client):
    global current_client, current_connection
    timer = None
    while True:
        try:
            # 接收數據
            #print("Debug: Waiting for data from the client...")
            data = connection.recv(1024)

            if timer is not None:
                timer.cancel()
            if not data:
                break

            print(data[0])
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # 精確到毫秒
            filename = f"/home/pi/{timestamp}.bin"
            with open(filename, 'wb') as f:
                f.write(data)

            timer = threading.Timer(5.0, merge_files_and_build_txt, args=['/home/pi/', '.bin'])  # set timer for 5 seconds
            timer.start()

            #print('Received data from {}: {}'.format(client, data.decode()))
        except ConnectionResetError:
            print('Client {} disconnected unexpectedly'.format(client))
            break

    # 檢查並關閉舊連接
    #print("Debug: Checking and closing old connections...")
    if client == current_client:
        connection.close()
        current_client = None
        current_connection = None
        

def LoopGetProfileFromHandBoard1():
    global current_client, current_connection
    port = 10005  # 更改此處的端口號

    server_socket = socket.socket()  
    server_socket.bind(('', port))  

    print('Server started')
    while True:
        #print("Debug: Listening for incoming connections...")
        server_socket.listen(2)
        conn, address = server_socket.accept()

        # 如果有舊的連接，則關閉
        #print("Debug: Checking and closing old connections...")
        if current_connection is not None:
            current_connection.close()
            print('Closed connection to {}'.format(current_client))

        # 儲存新的連接資訊
        current_connection = conn
        current_client = address
        print('Got connection from {}'.format(address))
        
        # 開始處理新的連接
        #print("Debug: Starting a new thread to handle the client...")
        threading.Thread(target=handle_client, args=(conn, address)).start()


def LoopGetProfileFromHandBoard():
    # 創建一個 socket 對象
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 定義監聽的端口
    port = 10005

    # 綁定端口
    s.bind(('', port))

    # 開始監聽，並設定最大連接請求數為 5
    s.listen(5)

    while True:
        # 當有客戶端連接時，返回一個新的socket對象和地址
        c, addr = s.accept()
        print('Got connection from', addr)

        timer = None
        while True:
            data = c.recv(1024)
            if timer is not None:
                timer.cancel()
            if not data:
                break

            print(data[0])
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # 精確到毫秒
            filename = f"/home/pi/{timestamp}.bin"
            with open(filename, 'wb') as f:
                f.write(data)

            timer = threading.Timer(5.0, merge_files_and_build_txt, args=['/home/pi/', '.bin'])  # set timer for 5 seconds
            timer.start()

        # 關閉與客戶端的連接
        c.close()

def LoopMergeFiles():
    while True:

        # 指定檔案路徑
        path = '/home/pi/'  # 你的檔案路徑

        # 獲取所有 .bin 檔案
        files = glob.glob(os.path.join(path, '*.bin'))

        # 將檔名解析為 datetime 對象並進行排序
        file_times = sorted((datetime.strptime(os.path.splitext(os.path.basename(f))[0], '%Y%m%d%H%M%S%f'), f) for f in files)

        if file_times:
            # 用於暫存將要合併的檔案列表
            files_to_merge = []
            # 上一個檔案時間
            prev_time = file_times[0][0]

            for curr_time, file in file_times[1:]:
                # 檢查時間差是否小於3秒
                if (curr_time - prev_time) <= timedelta(seconds=3):
                    # 如果還沒有添加過，則添加上一個檔案到列表中
                    if not files_to_merge or files_to_merge[-1] != file_times[file_times.index((prev_time, file))-1][1]:
                        files_to_merge.append(file_times[file_times.index((prev_time, file))-1][1])
                    # 添加當前檔案到列表中
                    files_to_merge.append(file)
                else:
                    # 如果有要合併的檔案，則合併並寫入新的檔案
                    if files_to_merge:
                        with open(f"{prev_time.strftime('%Y%m%d%H%M%S%f')[:-3]}_merged.bin", 'wb') as outfile:
                            for f in files_to_merge:
                                with open(f, 'rb') as infile:
                                    outfile.write(infile.read())
                        # 清空列表
                        files_to_merge = []
                # 更新上一個時間
                prev_time = curr_time

            # 檢查最後一個檔案
            if files_to_merge:
                with open(f"{prev_time.strftime('%Y%m%d%H%M%S%f')[:-3]}_merged.bin", 'wb') as outfile:
                    for f in files_to_merge:
                        with open(f, 'rb') as infile:
                            outfile.write(infile.read())

    time.sleep(1)

def LoopGetProfileFromHandBoard0():
    # 創建一個 socket 對象
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 定義監聽的端口
    port = 10005

    # 綁定端口
    s.bind(('', port))

    # 開始監聽，並設定最大連接請求數為 5
    s.listen(5)

    while True:
        # 當有客戶端連接時，返回一個新的socket對象和地址
        c, addr = s.accept()
        print('Got connection from', addr)

        # 獲取當前時間，並將其轉換為字串格式，作為檔名
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"/home/pi/{timestamp}.bin"

        # 繼續接收數據直到客戶端停止發送
        with open(filename, 'wb') as f:
            while True:
                data = c.recv(1024)
                if not data:
                    break
                # 將數據寫入檔案
                f.write(data)

        print(f'Data written to {filename}')

        # 關閉與客戶端的連接
        c.close()

def HandleControlCommand(data):
    print('Handle Command from "Control-1": ', data)

    if len(data) > 7:
        #find target device
        device_ = [device for device in devices if device['id'] == data[len(data)-1]]
        #if the target device exists
        if len(device_) == 1:
            device = device_[0]
            dataToSend = data[:len(data)-1]  #remove the last byte (device id)
            print('device ', data[len(data)-1], 'exists, pass command to it:', dataToSend)
            receivedData = SendDataAndGetResponse(sock=device['sock'], data=dataToSend)
            #print('get device response:', receivedData)
            print('----------------------------')
    else:
        print('Illegal Server0 command ', data)

def LoopReceiveControlClient():
    portNumber = 10004
    unpackerLength = struct.Struct('I')

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = ('0.0.0.0', portNumber)
    sock.bind(server_address)
    sock.listen(1)

    connection, client_address = sock.accept()
    while True:
        try:
            #receive
            data1 = connection.recv(unpackerLength.size)
            #print('received "%s"' % binascii.hexlify(data1))
            if(len(data1) >=4):
                unpacked_length = unpackerLength.unpack(data1)[0]
                #print('unpacked length:', unpacked_length)
                data2 = connection.recv(unpacked_length)
                #print('received "%s"' % binascii.hexlify(data2))
                unpackerContent = struct.Struct(str(unpacked_length) + 'B')
                unpacked_content = unpackerContent.unpack(data2)
                #print('Got message1:', unpacked_content)
                
                HandleControlCommand(unpacked_content)

                '''
                #send response
                data = (0x43, 0x43, 0x43, 0x43)
                packerContent = struct.Struct('I'+ str(len(data)) + 'B')
                packedContent = packerContent.pack(len(data), *data)
                try:
                    connection.send(packedContent)
                except socket.error as msg:
                    print('Caught exception socket.error : ', msg)
                '''
                
                #LoopHandleControlCommand(connection)

            #else:
            #    print('ABNORMAL COMMAND  is received')
                

        except:          
            connection.close()
            print("Control-1 is OFFLINE")
            break
        
def SetServerIp(ipAddr, gateway):
    #windows version
    '''
    print('Setting Server IP...')
    nic_configs = wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=True)
    nic = nic_configs[0]
    subnetmask = u'255.255.255.0'
    nic.EnableStatic(IPAddress=[ipAddr],SubnetMask=[subnetmask])
    nic.SetGateways(DefaultIPGateway=[gateway])
    '''

    #linux version1
    '''
    ip = IPRoute()
    index = ip.link_lookup(ifname='wlp3s0')[0]
    ip.addr('add', index, address=ipAddr, mask=24)
    ip.close()
    '''


    #linux version2
    from subprocess import call
    call(['ifconfig', 'wlp3s0', ipAddr, 'netmask', '255.255.255.0'])

def UpdateUi_(id, ip, info0, info1, info2, info3):
    #brake
    if id < 11:         
        if ip != 'null':
            uiBrakes[id-1]['labelId'].config(bg="lightgreen")
            uiBrakes[id-1]['labelName'].config(bg="lightgreen")
            uiBrakes[id-1]['labelIp'].config(bg="lightgreen")
            uiBrakes[id-1]['ip'].set(ip)
        else:
            '''
            uiBrakes[id-1]['labelId'].config(bg="lightgrey")
            uiBrakes[id-1]['labelName'].config(bg="lightgrey")
            uiBrakes[id-1]['labelIp'].config(bg="lightgrey")
            '''
            uiBrakes[id-1]['labelId'].config(bg="red")
            uiBrakes[id-1]['labelName'].config(bg="red")
            uiBrakes[id-1]['labelIp'].config(bg="red")

            uiBrakes[id-1]['ip'].set('')
    #axle
    elif id < 21:       
        if ip != 'null':
            uiAxles[id-11]['labelId'].config(bg="lightgreen")
            uiAxles[id-11]['labelName'].config(bg="lightgreen")
            uiAxles[id-11]['labelIp'].config(bg="lightgreen")
            uiAxles[id-11]['ip'].set(ip)
        else:
            '''
            uiAxles[id-11]['labelId'].config(bg="lightgrey")
            uiAxles[id-11]['labelName'].config(bg="lightgrey")
            uiAxles[id-11]['labelIp'].config(bg="lightgrey")
            '''
            uiAxles[id-11]['labelId'].config(bg="red")
            uiAxles[id-11]['labelName'].config(bg="red")
            uiAxles[id-11]['labelIp'].config(bg="red")

            uiAxles[id-11]['ip'].set('')
    #UPS
    elif id < 40:               
        if ip != 'null':
            uiUps[id-21]['labelId'].config(bg="lightgreen")
            uiUps[id-21]['labelName'].config(bg="lightgreen")
            uiUps[id-21]['labelIp'].config(bg="lightgreen")
            uiUps[id-21]['labelInfo0'].config(bg="lightgreen")
            uiUps[id-21]['labelInfo1'].config(bg="lightgreen")
            uiUps[id-21]['labelInfo2'].config(bg="lightgreen")
            uiUps[id-21]['labelInfo3'].config(bg="lightgreen")
            uiUps[id-21]['ip'].set(ip)
            uiUps[id-21]['info0'].set(info0)
            uiUps[id-21]['info1'].set(info1)
            uiUps[id-21]['info2'].set(info2)
            uiUps[id-21]['info3'].set(info3)

        else:
            '''
            uiUps[id-21]['labelId'].config(bg="lightgrey")
            uiUps[id-21]['labelName'].config(bg="lightgrey")
            uiUps[id-21]['labelIp'].config(bg="lightgrey")
            uiUps[id-21]['labelInfo0'].config(bg="lightgrey")
            uiUps[id-21]['labelInfo1'].config(bg="lightgrey")
            uiUps[id-21]['labelInfo2'].config(bg="lightgrey")
            uiUps[id-21]['labelInfo3'].config(bg="lightgrey")
            '''
            uiUps[id-21]['labelId'].config(bg="red")
            uiUps[id-21]['labelName'].config(bg="red")
            uiUps[id-21]['labelIp'].config(bg="red")
            uiUps[id-21]['labelInfo0'].config(bg="red")
            uiUps[id-21]['labelInfo1'].config(bg="red")
            uiUps[id-21]['labelInfo2'].config(bg="red")
            uiUps[id-21]['labelInfo3'].config(bg="red")

            uiUps[id-21]['ip'].set('')
            uiUps[id-21]['info0'].set('')
            uiUps[id-21]['info1'].set('')
            uiUps[id-21]['info2'].set('')
            uiUps[id-21]['info3'].set('')
    #turning
    elif id < 50:     
        if ip != 'null':
            uiTurnings[id-41]['labelId'].config(bg="lightgreen")
            uiTurnings[id-41]['labelName'].config(bg="lightgreen")
            uiTurnings[id-41]['labelIp'].config(bg="lightgreen")
            uiTurnings[id-41]['ip'].set(ip)
        else:
            uiTurnings[id-41]['labelId'].config(bg="red")
            uiTurnings[id-41]['labelName'].config(bg="red")
            uiTurnings[id-41]['labelIp'].config(bg="red")

            uiTurnings[id-41]['ip'].set('')
        

def UpdateUi(id, ip, info0='', info1='', info2='', info3=''):
    #print(info0,' ', info1,' ',info2,' ', info3)
    '''
    handler = Thread(target=UpdateUi_, args=(id, ip, info0, info1, info2, info3))
    handler.start()
    '''
    pass
    

def TurnLeftCommand():
    print('左轉')
    device11_ = [device for device in devices if device['id'] == 11]
    device12_ = [device for device in devices if device['id'] == 12]
    device13_ = [device for device in devices if device['id'] == 13]
    device14_ = [device for device in devices if device['id'] == 14]

    '''
    if len(device11_) == 1 and len(device12_) == 1 and len(device13_) == 1 and len(device14_) == 1:
        device11 = device11_[0]
        device12 = device12_[0]
        device13 = device13_[0]
        device14 = device14_[0]
        
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=1, pwm=0)
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=2, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=1, pwm=0)
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=2, pwm=pwmValue)
    '''
    if len(device11_) == 1:
        device11 = device11_[0]
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_11)
    if len(device12_) == 1:
        device12 = device12_[0]
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_12)
    if len(device13_) == 1:
        device13 = device13_[0]
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_13)
    if len(device14_) == 1:
        device14 = device14_[0]
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_14)

def TurnRightCommand():
    print('右轉')
    device11_ = [device for device in devices if device['id'] == 11]
    device12_ = [device for device in devices if device['id'] == 12]
    device13_ = [device for device in devices if device['id'] == 13]
    device14_ = [device for device in devices if device['id'] == 14]

    '''
    if len(device11_) == 1 and len(device12_) == 1 and len(device13_) == 1 and len(device14_) == 1:
        device11 = device11_[0]
        device12 = device12_[0]
        device13 = device13_[0]
        device14 = device14_[0]
        
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=0, pwm=0)
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=2, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=0, pwm=0)
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=2, pwm=pwmValue)
    '''

    #allow partial axiel devices
    if len(device11_) == 1:
        device11 = device11_[0]
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_11)
    if len(device12_) == 1:
        device12 = device12_[0]
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_12)
    if len(device13_) == 1:
        device13 = device13_[0]
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_13)
    if len(device14_) == 1:
        device14 = device14_[0]
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_14)

def GoForwardCommand():
    print('前進')
    device11_ = [device for device in devices if device['id'] == 11]
    device12_ = [device for device in devices if device['id'] == 12]
    device13_ = [device for device in devices if device['id'] == 13]
    device14_ = [device for device in devices if device['id'] == 14]
    '''
    if len(device11_) == 1 and len(device12_) == 1 and len(device13_) == 1 and len(device14_) == 1:
        device11 = device11_[0]
        device12 = device12_[0]
        device13 = device13_[0]
        device14 = device14_[0]
        
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=1, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=2, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=1, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=2, pwm=pwmValue)
    '''

    #allow partial axile devices
    if len(device11_) == 1:
        device11 = device11_[0]
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_11)
    if len(device12_) == 1:
        device12 = device12_[0]
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_12)
    if len(device13_) == 1:
        device13 = device13_[0]
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_13)
    if len(device14_) == 1:
        device14 = device14_[0]
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_14)

def GoBackwardCommand():
    print('後退')
    device11_ = [device for device in devices if device['id'] == 11]
    device12_ = [device for device in devices if device['id'] == 12]
    device13_ = [device for device in devices if device['id'] == 13]
    device14_ = [device for device in devices if device['id'] == 14]

    '''
    if len(device11_) == 1 and len(device12_) == 1 and len(device13_) == 1 and len(device14_) == 1:
        device11 = device11_[0]
        device12 = device12_[0]
        device13 = device13_[0]
        device14 = device14_[0]
        
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=2, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=1, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=2, pwm=pwmValue)
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=1, pwm=pwmValue)
    '''

    #allow partial axiel devices
    if len(device11_) == 1:
        device11 = device11_[0]
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_11)
    if len(device12_) == 1:
        device12 = device12_[0]
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_12)
    if len(device13_) == 1:
        device13 = device13_[0]
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], runDirection=1, pwm=pwmValue+AXILE_OFFSET_13)
    if len(device14_) == 1:
        device14 = device14_[0]
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], runDirection=2, pwm=pwmValue+AXILE_OFFSET_14)

def BrakeAllCommand():
    print('全剎車')
    device11_ = [device for device in devices if device['id'] == 11]
    device12_ = [device for device in devices if device['id'] == 12]
    device13_ = [device for device in devices if device['id'] == 13]
    device14_ = [device for device in devices if device['id'] == 14]

    '''
    if len(device11_) == 1 and len(device12_) == 1 and len(device13_) == 1 and len(device14_) == 1:
        device11 = device11_[0]
        device12 = device12_[0]
        device13 = device13_[0]
        device14 = device14_[0]
        
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], brake=True )
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], brake=True)
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], brake=True)
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], brake=True)
    '''

    #allow partial axiel devices
    if len(device11_) == 1:
        device11 = device11_[0]
        SendCommandSetAxleAndGetResponse(sock = device11['sock'], brake=True)
    if len(device12_) == 1:
        device12 = device12_[0]
        SendCommandSetAxleAndGetResponse(sock = device12['sock'], brake=True)
    if len(device13_) == 1:
        device13 = device13_[0]        
        SendCommandSetAxleAndGetResponse(sock = device13['sock'], brake=True)
    if len(device14_) == 1:
        device14 = device14_[0]        
        SendCommandSetAxleAndGetResponse(sock = device14['sock'], brake=True)



    

#=================Main program================
'''
#GUI
app = tk.Tk()
app.title('獨立輪車通訊網路 ID Server')
app.geometry('1000x750')

#show brakes
for id in range(1, 5):
    labelId = tk.Label(app, text=id, width=3, bg="lightgrey")
    labelId.place(x=40, y=20+30*(id-1))

    textName = '剎車馬達'+ str(id)
    name = tk.StringVar()
    name.set(textName)
    labelName = tk.Label(app, textvariable=name, width=15, bg="lightgrey")
    labelName.place(x=75, y=20+30*(id-1))

    textIp = ''
    ip = tk.StringVar()
    ip.set(textIp)
    labelIp = tk.Label(app, textvariable=ip, width=15, bg="lightgrey")
    labelIp.place(x=195, y=20+30*(id-1))


    
    newUiBrake={'id':id, #1-9
                'labelId':labelId,
                'name':name,
                'labelName':labelName,
                'ip':ip,
                'labelIp':labelIp
                }
    
    uiBrakes.append(newUiBrake)

#show axles
#tk.Scale(app, from_=0, to=200, orient="horizontal", width=10, length=100).grid(row=1, column=1)


for id in range(11, 15):
    labelId = tk.Label(app, text=id, width=3, bg="lightgrey")
    labelId.place(x=400+40, y=20+30*(id-11))

    textName = '輪軸馬達'+ str(id-10)
    name = tk.StringVar()
    name.set(textName)
    labelName = tk.Label(app, textvariable=name, width=15, bg="lightgrey")
    labelName.place(x=400+75, y=20+30*(id-11))

    textIp = ''
    ip = tk.StringVar()
    ip.set(textIp)
    labelIp = tk.Label(app, textvariable=ip, width=15, bg="lightgrey")
    labelIp.place(x=400+195, y=20+30*(id-11))


    
    newUiAxle={'id':id, #11-19
                'labelId':labelId,
                'name':name,
                'labelName':labelName,
                'ip':ip,
                'labelIp':labelIp
                }
    
    uiAxles.append(newUiAxle)


for id in range(41, 45):
    labelId = tk.Label(app, text=id, width=3, bg="lightgrey")
    labelId.place(x=840, y=20+30*(id-41))

    
    textName = '轉向馬達'+ str(id-40)
    name = tk.StringVar()
    name.set(textName)
    labelName = tk.Label(app, textvariable=name, width=15, bg="lightgrey")
    labelName.place(x=800+75, y=20+30*(id-41))

    textIp = ''
    ip = tk.StringVar()
    ip.set(textIp)
    labelIp = tk.Label(app, textvariable=ip, width=15, bg="lightgrey")
    labelIp.place(x=800+195, y=20+30*(id-41))

    
    newUiTurning={'id':id, #11-19
                'labelId':labelId,
                'name':name,
                'labelName':labelName,
                'ip':ip,
                'labelIp':labelIp
                }
    
    uiTurnings.append(newUiTurning)
    
    
    

#show ups
labelIdNote = tk.Label(app, text='ID', width=3)
labelIdNote.place(x=40, y=160+20)

labelNameNote = tk.Label(app, text='Name', width=15)
labelNameNote.place(x=75, y=160+20)

labelIpNote = tk.Label(app, text='IP', width=15)
labelIpNote.place(x=195, y=160+20)


labelInfo0Note = tk.Label(app, text='Vin', width=5)
labelInfo0Note.place(x=320, y=160+20)

labelInfo1Note = tk.Label(app, text='Iin', width=5)
labelInfo1Note.place(x=380, y=160+20)

labelInfo2Note = tk.Label(app, text='Vout', width=5)
labelInfo2Note.place(x=440, y=160+20)

labelInfo3Note = tk.Label(app, text='Iout', width=5)
labelInfo3Note.place(x=500, y=160+20)

for id in range(21, 37):
    labelId = tk.Label(app, text=id, width=3, bg="lightgrey")
    labelId.place(x=40, y=160+50+30*(id-21))

    textName = 'UPS'+ str(id-20)
    name = tk.StringVar()
    name.set(textName)
    labelName = tk.Label(app, textvariable=name, width=15, bg="lightgrey")
    labelName.place(x=75, y=160+50+30*(id-21))

    textIp = ''
    ip = tk.StringVar()
    ip.set(textIp)
    labelIp = tk.Label(app, textvariable=ip, width=15, bg="lightgrey")
    labelIp.place(x=195, y=160+50+30*(id-21))

    textInfo0 = ''
    info0 = tk.StringVar()
    info0.set(textInfo0)
    labelInfo0 = tk.Label(app, textvariable=info0, width=5, bg="lightgrey")
    labelInfo0.place(x=320, y=160+50+30*(id-21))

    textInfo1 = ''
    info1 = tk.StringVar()
    info1.set(textInfo1)
    labelInfo1 = tk.Label(app, textvariable=info1, width=5, bg="lightgrey")
    labelInfo1.place(x=380, y=160+50+30*(id-21))

    textInfo2 = ''
    info2 = tk.StringVar()
    info2.set(textInfo2)
    labelInfo2 = tk.Label(app, textvariable=info2, width=5, bg="lightgrey")
    labelInfo2.place(x=440, y=160+50+30*(id-21))
    
    textInfo3 = ''
    info3 = tk.StringVar()
    info3.set(textInfo3)
    labelInfo3 = tk.Label(app, textvariable=info3, width=5, bg="lightgrey")
    labelInfo3.place(x=500, y=160+50+30*(id-21))

    newUiUps={'id':id, #21-36
                'labelId':labelId,
                'name':name,
                'labelName':labelName,
                'ip':ip,
                'labelIp':labelIp,
                'info0':info0,
                'labelInfo0':labelInfo0,
                'info1':info1,
                'labelInfo1':labelInfo1,
                'info2':info2,
                'labelInfo2':labelInfo2,
                'info3':info3,
                'labelInfo3':labelInfo3,
                }
    
    uiUps.append(newUiUps)


'''

#------------------main funcs------------------
#set up IP (skipped now)
#SetServerIp(ipAddr=serverIp, gateway=gatewayIp)

MakeSureGotLanIp()

#run routines to accept connections from devices
handler1 = Thread(target=LoopGetConnectionFromADecice)
handler1.start()

handler2 = Thread(target=LoopGetAliveSignal)
handler2.start()

#handler3 = Thread(target=LoopCheckDeviceAvailibility)
#handler3.start()

handler4 = Thread(target=LoopSendCommandGetUpsInfo)
handler4.start()

#handler5 = Thread(target=LoopHandleJoystickEvents)
#handler5.start()

handler6 = Thread(target=LoopReceiveControlClient)
handler6.start()

handler7 = Thread(target=LoopGetProfileFromHandBoard1)
handler7.start()

#handler8 = Thread(target=863)
#handler8.start()
#------------------end main funcs---------------
'''
app.mainloop()
'''    


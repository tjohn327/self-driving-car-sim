import socket
import json
import cv2
from pynput import keyboard
import numpy as np
import threading, queue
import time
import signal
import inputs
import sys

UDP_IP = "0.0.0.0"
UDP_PORT = 11500
# UDP_SIM_IP = "192.168.1.106"
# UDP_SIM_PORT = 11000
UDP_SIM_IP = "192.168.1.151"
UDP_SIM_PORT = 11800
FRAME_SIZE = 1100
HEADER_SIZE = 4
FPS = 30

imageQueue = queue.Queue()
imageFragQueue = queue.Queue()
img = None
steering = 0.0
throttle = 0.0
frame_time = 20.0

run = True

def sigHandler(sig, frame):
    global run
    if run:
        print ("Terminating...")
        run = False 
    else: 
        print ("Force quitting...")
        sys.exit(1)


def on_press(key):
    global steering, throttle
    try:
        if key.char == 'w':
            throttle = 0.8
        if key.char == 's':
            throttle = -1
        if key.char == 'a':
            steering = -1
        if key.char == 'd':
            steering = 1
    except:
        pass

def on_release(key):
    global run, steering, throttle
    if key == keyboard.Key.esc:
        # Stop listener
        run = False
        print("Terminating...")
        return False
    try:
        if key.char == 'w':
            throttle = 0
        if key.char == 's':
            throttle = 0
        if key.char == 'a':
            steering = 0
        if key.char == 'd':
            steering = 0
    except:
        pass
    
def receive_image_thread(sock, imageFragQueue):
    global run
    print("Started receiving stream")    
    while run:        
        try:
            sock.settimeout(2)
            buf = sock.recv(FRAME_SIZE+100)  
            imageFragQueue.put(buf)            
        except Exception as ex:            
            if str(ex) != "timed out":
                # print(ex)
                pass

def image_process_thread(imageFragQueue):
    global run, frame_time
    print("Started processing stream")    
    currentIndex = 0
    currentFrag = 0
    image = b''
    startTime = 0
    while run:        
        try:
            buf = imageFragQueue.get(timeout=2)        
            index = int.from_bytes(buf[0:2],"big")
            frag = int.from_bytes(buf[2:4],"big")
            # print(frag)
            # print(index, frag, len(buf))
            if index == currentIndex:
                currentFrag = frag
                if frag > 1:
                    image += buf[HEADER_SIZE:]
                if frag == 1:
                    image += buf[HEADER_SIZE:] 
                    frame_time = (time.time()-startTime)*1000           
                    imageQueue.put(image)
                    image = b''
                
            if index != currentIndex:   
                if currentFrag != 1:
                    print("incomplete frame")
                    print(index, frag, len(buf))
                    frame_time = 20
                startTime = time.time()
                currentIndex = index     
                # print(currentIndex, frag)           
                image = b''
                image += buf[HEADER_SIZE:]
            
        except Exception as ex:            
            if str(ex) != "timed out":
                # print(ex)
                pass

def display_image_thread(imageQueue):
    global run, frame_time
    cv2.namedWindow('Remote Control', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Remote Control', 640 , 480)
    while run:        
        try:
            image = imageQueue.get(timeout=2)
            nparr = np.frombuffer(image, np.uint8)            
            img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            cv2.imshow('Remote Control',img)
            cv2.waitKey(1)
        except Exception as ex:
            frame_time = 10
            cv2.waitKey(1)
            print(ex)
        
def scaleAxis(val, src = (-32768.0, 32767), dst = (-1.0, +1.0)):
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]  

def handleJoystick(pads):
    global run, throttle, steering, frame_time
    while run:
        if len(pads)>0:
            events = inputs.get_gamepad()
            for event in events:
                # print(event.ev_type, event.code, event.state)
                if event.code == "ABS_Z":
                    throttle = scaleAxis(float(event.state),(0.0,255.0),(0.0,1.0))
                if event.code == "ABS_RZ":
                    throttle = scaleAxis(float(event.state),(0.0,255.0),(0.0,-1.0))
                if event.code == "ABS_X":
                    steering = scaleAxis(float(event.state))                
                if event.code == "BTN_START":
                    run = False
                    print("Terminating...")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigHandler)

    sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP, UDP_PORT))
    
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release)
    listener.start()

    receive_thread = threading.Thread(target=receive_image_thread, args=(sock,imageFragQueue))
    process_thread = threading.Thread(target=image_process_thread, args=(imageFragQueue,))
    image_thread = threading.Thread(target=display_image_thread, args=(imageQueue,))
    image_thread.start()
    process_thread.start()
    receive_thread.start()
    
    pads = inputs.devices.gamepads
    if len(pads) > 0:
        print("Gamepad found, using it for control")
        print("Press 'back' to exit")
        joystick_thread = threading.Thread(target=handleJoystick, args=(pads,))
        joystick_thread.start()

    while run:
        try:
            message = {
                "steering_angle" : steering,
                "throttle": throttle,
                "frame_time": frame_time
            }
            sendData = json.dumps(message).encode('utf-8')
            sock.sendto(sendData, (UDP_SIM_IP, UDP_SIM_PORT))
            time.sleep(1.0/FPS)
        except:
            pass

    cv2.destroyAllWindows()
    receive_thread.join()
    process_thread.join()
    image_thread.join()
    joystick_thread.join()
    
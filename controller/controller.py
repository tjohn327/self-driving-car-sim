import socket
import json
import cv2
from pynput import keyboard
import numpy as np
import threading, queue
import time
import signal
import inputs
import copy
import sys

UDP_IP = "0.0.0.0"
UDP_PORT = 11500
UDP_SIM_IP = "192.168.X.XXX"
UDP_SIM_PORT = 11800
FRAME_SIZE = 1100
HEADER_SIZE = 4
FPS = 30

imageQueue = queue.Queue()
img = None
steering = 0.0
throttle = 0.0

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
    
def receive_image_thread(sock, imageQueue):
    global run
    print("Started receiving stream")    
    currentIndex = 0
    currentFrag = 0
    image = b''
    while run:        
        try:
            sock.settimeout(2)
            buf = sock.recv(FRAME_SIZE+1000)            
            index = int.from_bytes(buf[0:2],"big")
            frag = int.from_bytes(buf[2:4],"big")
            # print(index, frag, len(buf))
            if index == currentIndex:
                currentFrag = frag
                if frag > 1:
                    image += buf[HEADER_SIZE:]
                if frag == 1:
                    image += buf[HEADER_SIZE:]
                    imageQueue.put(image)
                    image = b''
                
            if index != currentIndex:   
                if currentFrag != 1:
                    print("not complete")
                    print(index, frag, len(buf))
                currentIndex = index                
                image = b''
                image += buf[HEADER_SIZE:]
            
        except Exception as ex:            
            if str(ex) != "timed out":
                print(ex)

def display_image_thread(imageQueue):
    global run
    cv2.namedWindow('Remote Control', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Remote Control', 640 , 480)
    while run:        
        try:
            image = imageQueue.get(timeout=1)
            nparr = np.frombuffer(image, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            cv2.imshow('Remote Control',img)
            cv2.waitKey(1)
        except Exception as ex:
            cv2.waitKey(1)
            print(ex)
        
def scaleAxis(val, src = (-32768.0, 32767), dst = (-1.0, +1.0)):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]  

def handleJoystick(pads):
    global run, throttle, steering
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

    receive_thread = threading.Thread(target=receive_image_thread, args=(sock,imageQueue))
    image_thread = threading.Thread(target=display_image_thread, args=(imageQueue,))
    image_thread.start()
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
                "throttle": throttle
            }
            sendData = json.dumps(message).encode('utf-8')
            # print(sendData)
            sock.sendto(sendData, (UDP_SIM_IP, UDP_SIM_PORT))
            # cv2.waitKey(int(1000/FPS))
            time.sleep(1.0/FPS)
        except:
            pass
    cv2.destroyAllWindows()
    receive_thread.join()
    image_thread.join()
    joystick_thread.join()
    

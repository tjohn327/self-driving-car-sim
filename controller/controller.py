import socket
import json
import base64
import cv2
from numpy.core.fromnumeric import size
from numpy.testing._private.utils import clear_and_catch_warnings
from pynput import keyboard
import numpy as np
import base64
import threading
import time
import signal
import sys



UDP_IP = "0.0.0.0"
UDP_PORT = 11500
UDP_SIM_IP = "0.0.0.0"
UDP_SIM_PORT = 11000

FPS = 30

img = None
steering = 0.0
throttle = 0.0

run = True



def signal_handler(sig, frame):
    global run
    run = False

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
    
def receive_image_thread(sock):
    cv2.namedWindow('Remote Control', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Remote Control', 400, 300)
    while run:
        try:
            sock.settimeout(5)
            data = sock.recv(30000)
            data = json.loads(data)
            print("Speed: {0}  Steering: {1}".format( data["speed"] ,data["steering_angle"]))
            img_data = base64.b64decode(data["image"])
            # print(sys.getsizeof(img_data))
            nparr = np.fromstring(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            cv2.imshow('Remote Control',img)
            cv2.waitKey(int(1000/60))
            
        except:
            cv2.waitKey(int(1000/60))
            pass
        
        

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)

    sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_IP, UDP_PORT))
    
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release)
    listener.start()

    receive_thread = threading.Thread(target=receive_image_thread, args=(sock,))
    receive_thread.start()

    while run:
        message = {
            "steering_angle" : steering,
            "throttle": throttle
        }
        sendData = json.dumps(message).encode('utf-8')
        # print(sendData)
        sock.sendto(sendData, (UDP_SIM_IP, UDP_SIM_PORT))
        # cv2.waitKey(int(1000/FPS))
        time.sleep(1.0/FPS)
        
    sock.close()
    cv2.destroyAllWindows()

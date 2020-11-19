import socket
import json
import base64
import cv2
from pynput import keyboard
import numpy as np
import base64

UDP_IP = "127.0.0.1"
UDP_PORT = 11500
UDP_SIM_PORT = 11000

FPS = 30
sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

steering = 0.0
throttle = 0.0

run = True
cv2.namedWindow('Remote Control', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Remote Control', 500, 300)

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
    

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

while run:
    message = {
        "steering_angle" : steering,
        "throttle": throttle
    }

    sendData = json.dumps(message).encode('utf-8')
    sock.sendto(sendData, (UDP_IP, UDP_SIM_PORT))

    data, addr = sock.recvfrom(1024000)
    data = json.loads(data)
    print("Speed: {0}  Steering: {1}".format( data["speed"] ,data["steering_angle"]))

    img_data = base64.b64decode(data["image"])
    nparr = np.fromstring(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)

    cv2.imshow('Remote Control',img)
    cv2.waitKey(int(1000/FPS))

sock.close()
cv2.destroyAllWindows()

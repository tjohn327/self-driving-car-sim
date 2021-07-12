import socket
import json
import numpy as np
import threading, queue
import time
import signal
import sys
import logging
import cv2

MODE = 1
HOST = "0.0.0.0"
HOST_PORT = 11010
CONTROL_SEND_IP = "192.168.1.106"
CONTROL_SEND_PORT = 11000

REMOTE_MODE= 1
REMOTE_PROXY_MODE = 2
DEMO_SERVER_MODE = 3
DISPLAY_MODE = 4

# Default Remote Mode
if MODE == REMOTE_MODE:
    DISPLAY_IMAGE =True
    CONTROL_SERVER = False
    DEMO_SERVER = False
    KEYBOARD = True
    JOYSTICK = True
    SEND_CONTROL = True
elif MODE == REMOTE_PROXY_MODE:
    IMAGE_SEND_IP = "192.168.1.106"
    IMAGE_SEND_PORT = 11030
    CONTROL_RECEIVE_PORT = 11020
    DISPLAY_IMAGE =False
    CONTROL_SERVER = True
    DEMO_SERVER = True
    KEYBOARD = False
    JOYSTICK = False
    SEND_CONTROL = True
elif MODE == DEMO_SERVER_MODE:
    HOST_PORT = 11030
    CONTROL_SEND_PORT = 11020
    CONTROL_SEND_IP = "192.168.1.188"
    DISPLAY_IMAGE =True
    CONTROL_SERVER = False
    DEMO_SERVER = False
    KEYBOARD = True
    JOYSTICK = True
    SEND_CONTROL = True
elif MODE == DISPLAY_MODE:
    HOST_PORT = 11040
    DISPLAY_IMAGE =True
    CONTROL_SERVER = False
    DEMO_SERVER = False
    KEYBOARD = False
    JOYSTICK = False
    SEND_CONTROL = False

if DISPLAY_IMAGE:
    import cv2
if KEYBOARD:
    from pynput import keyboard
if JOYSTICK:
    import inputs

FRAME_SIZE = 1100
HEADER_SIZE = 4
FPS = 30

imageDisplayQueue = queue.Queue()
imageFragQueue = queue.Queue()
demoImageFragQueue = queue.Queue()
img = None
steering = 0.0
throttle = 0.0
frame_time = 20.0
reset = False

run = True

def sigHandler(sig, frame):
    global run
    if run:
        logging.info("Terminating...")
        run = False 
    else: 
        logging.info("Force quitting...")
        sys.exit(1)


def on_press(key):
    global steering, throttle, reset
    try:
        if key.char == 'w':
            throttle = 0.8
        if key.char == 's':
            throttle = -1
        if key.char == 'a':
            steering = -1
        if key.char == 'd':
            steering = 1
        if key.char == 'r':
            reset = True
    except:
        pass

def on_release(key):
    global run, steering, throttle, reset
    if key == keyboard.Key.esc:
        # Stop listener
        run = False
        logging.info("Terminating...")
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
        if key.char == 'r':
            reset = False
    except:
        pass

def receive_control_thread(control_sock):
    global run, steering, throttle, reset, frame_time
    logging.info("Started receiving control")    
    while run:        
        try:
            control_sock.settimeout(1)
            buf = control_sock.recv(1000)
            data = json.loads(buf)
            if data["steering_angle"] >= -1 and  data["steering_angle"] <= 1:
                steering = data["steering_angle"]
            if data["throttle"] >= -1 and  data["throttle"] <= 1:
                throttle = data["throttle"]
            # if data["frame_time"] >= 0 and  data["frame_time"] <= 500:
            #     frame_time = data["frame_time"]
            if data["reset"]:
                reset = True
        except Exception as ex:
            if str(ex) == "timed out":
                logging.warning("Control Receive: "+ str(ex))
            else:
                logging.error("Control Receive: "+ str(ex))                        
    
def receive_image_thread(sock, imageFragQueue, demoImageFragQueue):
    global run
    logging.info("Started receiving stream")    
    while run:        
        try:
            sock.settimeout(1)
            buf = sock.recv(FRAME_SIZE+100)  
            imageFragQueue.put(buf) 
            if DEMO_SERVER:
                demoImageFragQueue.put(buf)           
        except Exception as ex:                     
            if str(ex) == "timed out":
                logging.warning("Image Receive: "+ str(ex))  
            else:
                logging.error("Image Receive: "+ str(ex))                       

def image_process_thread(imageFragQueue, imageDisplayQueue):
    global run, frame_time, DEMO_SERVER
    logging.info("Started processing stream")    
    currentIndex = 0
    currentFrag = 0
    image = b''
    startTime = 0
    while run:        
        try:
            buf = imageFragQueue.get(timeout=1)        
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
                    nparr = np.frombuffer(image, np.uint8)            
                    img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
                    if img is not None:
                        img_end = img[-1][-1]
                        if not all(i == 128 for i in img_end): #check if image is corrupted
                            if DISPLAY_IMAGE:
                                imageDisplayQueue.put(img)                        
                    image = b''
                
            if index != currentIndex:   
                if currentFrag != 1:
                    logging.info("Incomplete frame: {} {} {}".format(index, frag, len(buf)))
                    frame_time = 20
                startTime = time.time()
                currentIndex = index     
                # print(currentIndex, frag)           
                image = b''
                image += buf[HEADER_SIZE:]
            
        except Exception as ex:      
            if str(ex) == "":
                continue      
            if str(ex) == "timed out":
                logging.warning("Image Processing: "+ str(ex)) 
            else: 
                logging.error("Image Processing: "+ str(ex))        

def display_image_thread(imageDisplayQueue):
    global run
    cv2.namedWindow('Remote Control', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Remote Control', 640 , 480)
    while run:        
        try:
            image = imageDisplayQueue.get(timeout=1)            
            cv2.imshow('Remote Control',image)
            cv2.waitKey(1)
        except Exception as ex:
            if str(ex) == "":
                continue
            if str(ex) == "timed out":
                logging.warning("Image Display: "+ str(ex))  
            else:
                logging.error("Image Display: "+ str(ex))   
            cv2.waitKey(1)

def demo_image_thread(sock, demoImageFragQueue):
    global run, frame_time
    logging.info("Sending images to demo server started")
    while run:        
        try:
            buf = demoImageFragQueue.get(timeout=1) 
            sock.sendto(buf, (IMAGE_SEND_IP, IMAGE_SEND_PORT))                  
        except Exception as ex:
            if str(ex) == "":
                continue
            if str(ex) == "timed out":
                frame_time = 10                
                logging.info("Demo Image: "+ str(ex))
            else:
                logging.error("Demo Image: "+ str(ex))

        
def scaleAxis(val, src = (-32768.0, 32767), dst = (-1.0, +1.0)):
    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]  

def handleJoystick(pads):
    global run, throttle, steering, reset
    if len(pads)>0:
        while run:
            events = inputs.get_gamepad()
            for event in events:
                # print(event.ev_type, event.code, event.state)
                if event.code == "ABS_Z":
                    throttle = scaleAxis(float(event.state),(0.0,255.0),(0.0,1.0))
                if event.code == "ABS_RZ":
                    throttle = scaleAxis(float(event.state),(0.0,255.0),(0.0,-1.0))
                if event.code == "ABS_X":
                    steering = scaleAxis(float(event.state)) 
                if event.code == "BTN_SELECT":
                    if event.state == 1:
                        reset = True
                if event.code == "BTN_START":
                    run = False
                    logging.info("Terminating...")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigHandler)
    logging.basicConfig(level=logging.INFO)
    sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    sock.bind((HOST, HOST_PORT))

    receive_thread = threading.Thread(target=receive_image_thread, args=(sock,imageFragQueue, demoImageFragQueue))    
    receive_thread.start()

    if DISPLAY_IMAGE:
        image_thread = threading.Thread(target=display_image_thread, args=(imageDisplayQueue,))
        process_thread = threading.Thread(target=image_process_thread, args=(imageFragQueue,imageDisplayQueue))    
        process_thread.start()
        image_thread.start()

    listener = None
    if KEYBOARD:
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release)
        listener.start()

    control_thread = None
    if CONTROL_SERVER:
        control_sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP
        control_sock.bind((HOST, CONTROL_RECEIVE_PORT))
        control_thread = threading.Thread(target=receive_control_thread, args=(control_sock,))
        control_thread.start()
    
    demo_image_send_thread = None
    if DEMO_SERVER:
        demo_image_sock = socket.socket(socket.AF_INET, # Internet
                            socket.SOCK_DGRAM) # UDP
        demo_image_sock.bind((HOST, IMAGE_SEND_PORT))
        demo_image_send_thread = threading.Thread(target=demo_image_thread, args=(demo_image_sock,demoImageFragQueue))
        demo_image_send_thread.start()
    
    joystick_thread = None
    if JOYSTICK:
        pads = inputs.devices.gamepads
        if len(pads) > 0 :
            logging.info("Gamepad found, using it for control")
            logging.info("Press 'back' to exit")
            joystick_thread = threading.Thread(target=handleJoystick, args=(pads,))
            joystick_thread.start()

    if SEND_CONTROL:
        while run:
            try:
                message = {
                    "steering_angle" : steering,
                    "throttle": throttle,
                    "frame_time": frame_time,
                    "reset" : reset
                }
                sendData = json.dumps(message).encode('utf-8')
                sock.sendto(sendData, (CONTROL_SEND_IP, CONTROL_SEND_PORT))
                if reset:
                    reset = False
                time.sleep(1.0/FPS)
            except Exception as ex:
                logging.error("Send Control: "+ str(ex))
                time.sleep(1.0/FPS)
    else:
        while run:
            time.sleep(1)
    
    receive_thread.join()    
    if DISPLAY_IMAGE:
        image_thread.join()
        process_thread.join()
        cv2.destroyAllWindows()
    if DEMO_SERVER:
        demo_image_send_thread.join()
    if JOYSTICK and joystick_thread is not None:
        joystick_thread.join()
    if CONTROL_SERVER:        
        control_thread.join()
    
import socket
import json
import cv2
import numpy as np
import threading, queue
import time
import signal
import sys

UDP_SIM_IP = "0.0.0.0"
UDP_SIM_PORT = 16000
UDP_SIM_PORT = 11750

FRAME_SIZE = 1100
HEADER_SIZE = 4
FPS = 30

imageQueue = queue.Queue()
img = None
run = True

def sigHandler(sig, frame):
    global run
    if run:
        print ("Terminating...")
        run = False 
    else: 
        print ("Force quitting...")
        sys.exit(1)

    
def receive_image_thread(sock, imageQueue):
    global run
    print("Started receiving stream")    
    while run:        
        try:
            sock.settimeout(2)
            buf = sock.recv(50000)  
            imageQueue.put(buf)            
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
        

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigHandler)

    sock = socket.socket(socket.AF_INET, # Internet
                        socket.SOCK_DGRAM) # UDP
    sock.bind((UDP_SIM_IP, UDP_SIM_PORT))

    receive_thread = threading.Thread(target=receive_image_thread, args=(sock,imageQueue))
    image_thread = threading.Thread(target=display_image_thread, args=(imageQueue,))
   
    image_thread.start()
    receive_thread.start()
    
    while True:
        time.sleep(1)
        
    receive_thread.join()
    image_thread.join()
    
# Driving Simulator for SCION multipath demo

This is a modified version of [Udacity Self driving car sim](https://github.com/udacity/self-driving-car-sim). Original [README](./README_ORG.md).

![Car Simulator_demo](./sim_demo.gif)

### Control and telemetry

The sim listens on 0.0.0.0:11000 for control message over UDP and sends the front camera image back.

Control message example:

```json
{
   "steering_angle":0.9,
   "throttle":0.8,
   "reset": false, //resets the sim if true
   "frame_time": 10 //time taken to receive last frame in milliseconds
}
```

steering_angle and throttle values ∈ [-1,1]

### Remote Control

The python script [controller.py](./controller/controller.py) demonstrates a basic remote control using keyboard inputs or xbox controller. 'CONTROL_SEND_IP' should be changed to the IP address of the car simulator. To use this script, first run the simulator, then run this script and use W, A, S & D keys to control the car in the simulator.

### Modifying the sim

To modify the sim please use Unity 2019.4 and Visual Studio 2017.

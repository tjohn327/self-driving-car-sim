## Driving Simulator for SCION multipath demo

This is a modified version of [Udacity Self driving car sim](https://github.com/udacity/self-driving-car-sim). Original [README](./README_ORG.md).

![Car Simulator_demo](./sim_demo.gif)

### Control and telemetry

The sim listens on 127.0.0.1:11500 for control message over UDP and sends telemetry message back.

Control message example:

```json
{
   "steering_angle":0.9,
   "throttle":0.8
}
```

Telemetry message example:

```json
{
   "steering_angle":25,
   "throttle":1,
   "speed":30,
   "image":"image from front facing camera as base64 encoded string"
}
```

steering_angle and throttle values ∈ [-1,1]

### Remote Control

The python script [controller.py](./controller/controller.py) demonstrates a basic remote control using keyboard inputs. To use this script, first run the simulator and select a track, then run this script and use W, A, S & D keys to control the car in the simulator.

### Modifying the sim

To modify the sim please use Unity 5.5.1f1 and Visual Studio 2015.

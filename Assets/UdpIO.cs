﻿using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Net;
using System.Net.Sockets;
using UnityStandardAssets.Vehicles.Car;
using System.Threading;
using System.Text;

public class UdpIO : MonoBehaviour {
    public CarRemoteControl CarRemoteControl;
    public Camera FrontFacingCamera;
    private float acceleration;
    private float steeringAngle;
    private CarController _carController;

    private volatile bool connected;
    private Thread udpReceiveThread;
    private const int listenPort = 11000;
    private const int sendPort = 11002;
    IPEndPoint sender;
    private volatile byte[] telemetry;

    UdpClient udpClient;


	// Use this for initialization
	void Start () {
        Application.targetFrameRate = 30;
        acceleration = 0;
        steeringAngle = 0;
        _carController = CarRemoteControl.GetComponent<CarController>();
        connected = false;
        Connect();
    }

    // Update is called once per frame
    void Update()
    {
        telemetry = GetTelemetry();
        if (connected && telemetry != null && sender != null)
        {
            try
            {
                udpClient.Send(telemetry, telemetry.Length, sender);
            }
            catch (Exception)
            {
                // ignore
            }
            
        }

    }

    public void OnDestroy()
    {
        if (udpReceiveThread != null) { udpReceiveThread.Abort(); }
        udpClient.Close();
    }

    public void OnApplicationQuit()
    {
        Close();
    }

    private void Connect()
    {
        IPEndPoint ipLocalEndPoint = new IPEndPoint(IPAddress.Parse("0.0.0.0"), listenPort);
        udpClient = new UdpClient(ipLocalEndPoint);
        connected = true;
        udpReceiveThread = new Thread(RunUdpServer);
        udpReceiveThread.Start(udpClient);
    }

    public void Close()
    {
        connected = false;
        udpClient.Close();
    }

    private void RunUdpServer(object obj)
    {
        UdpClient udpClient = (UdpClient)obj;
        sender = new IPEndPoint(IPAddress.Any, 0);

        while (connected)
        {
            byte[] dataIn = udpClient.Receive(ref sender);
            SetCarControl(dataIn);
        }
        udpClient.Close();
    }

    private void SetCarControl(byte[] data)
    {        
        try
        {
            string json = Encoding.UTF8.GetString(data, 0, data.Length);
            CarControlData control = JsonUtility.FromJson<CarControlData>(json);
            CarRemoteControl.SteeringAngle = control.steering_angle;
            CarRemoteControl.Acceleration = control.throttle;
        }
        catch (Exception e)
        {
            Debug.Log(e.Message);
        }       
    }

    private byte[] GetTelemetry()
    {
        Dictionary<string, string> data = new Dictionary<string, string>();
        data["steering_angle"] = _carController.CurrentSteerAngle.ToString("N4");
        data["throttle"] = _carController.AccelInput.ToString("N4");
        data["speed"] = _carController.CurrentSpeed.ToString("N4");
        data["image"] = Convert.ToBase64String(CameraHelper.CaptureFrame(FrontFacingCamera));
        JSONObject json = new JSONObject(data);
        byte[] dataOut = Encoding.UTF8.GetBytes(json.ToString());
        return dataOut;
    }
}

[Serializable]
public class CarControlData
{
    public float steering_angle;
    public float throttle;
}

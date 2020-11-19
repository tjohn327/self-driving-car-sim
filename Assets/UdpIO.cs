using System.Collections;
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
    private Thread udpThread;
    private const int listenPort = 11000;
    private volatile byte[] telemetry;

    UdpClient udpClient;


	// Use this for initialization
	void Start () {
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

    }

    public void OnDestroy()
    {
        if (udpThread != null) { udpThread.Abort(); }
        udpClient.Close();
    }

    public void OnApplicationQuit()
    {
        Close();
    }

    private void Connect()
    {
        udpClient = new UdpClient(listenPort);
        connected = true;
        udpThread = new Thread(RunUdpServer);
        udpThread.Start(udpClient);
    }

    public void Close()
    {
        connected = false;
    }

    private void RunUdpServer(object obj)
    {
        UdpClient udpClient = (UdpClient)obj;
        IPEndPoint sender = new IPEndPoint(IPAddress.Any, 0);

        while (connected)
        {
            byte[] dataIn = udpClient.Receive(ref sender);
            SetCarControl(dataIn);
            if (telemetry != null)
            {
                udpClient.Send(telemetry, telemetry.Length, sender);
            }
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

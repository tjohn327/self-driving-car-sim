using System;
using System.Collections;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityStandardAssets.Vehicles.Car;

public class UdpIO : MonoBehaviour
{
    public CarRemoteControl CarRemoteControl;
    public Camera FrontFacingCamera;
    //public Camera SimCamera;
    private float acceleration;
    private float steeringAngle;
    private float frame_time;
    private int quality = 35;
    private CarController carController;
    private volatile bool reset = false;

    private volatile bool connected;
    private volatile bool received;
    private Thread udpReceiveThread;
    private const int listenPort = 11000;
    private const float target_frame_time = 10;
    private const int fps = 40;
    IPEndPoint remoteSender;
    //IPEndPoint SimCameraSender;
    //private volatile byte[] telemetry;
    //private volatile byte[][] fragments;

    UdpClient udpClient;
    //UdpClient simCamUdpClient;
    private const int frameSize = 1100;
    private const int headerSize = 4;
    private const int payloadSize = frameSize - headerSize;
    //private const string SimCameraIP = "192.168.1.192";
    //private const int SimCameraPort = 11040;
    private const int maxImageQuality = 30;

    private UInt16 frontCameraSeq = 0;
    private UInt16 mainCameraSeq = 0;


    // Use this for initialization
    void Start()
    {
        Application.targetFrameRate = fps;
        acceleration = 0;
        steeringAngle = 0;
        carController = CarRemoteControl.GetComponent<CarController>();
        connected = false;
        received = false;       
        Connect();
    }

    // Update is called once per frame
    void Update()
    {
        setQquality();
        FrontFacingCamera.Render();
        //SimCamera.Render();
        //var simCameraImage = CameraHelper.CaptureFrame(SimCamera, maxImageQuality);
        var frontCameraImage = CameraHelper.CaptureFrame(FrontFacingCamera, quality);
        /*
        try
        {            
            FragmentAndSendImage(simCameraImage, mainCameraSeq, simCamUdpClient, SimCameraSender);
            if (mainCameraSeq >= 65534)
            {
                mainCameraSeq = 0;
            }
            else
            {
                mainCameraSeq++;
            }
        }
        catch (Exception ex)
        {
            Debug.Log(ex.ToString());
        }
        */
        if (received && connected && remoteSender != null)
        {
            try
            {                
                FragmentAndSendImage(frontCameraImage, frontCameraSeq, udpClient, remoteSender);                
                if (frontCameraSeq >= 65534)
                {
                    frontCameraSeq = 0;
                }
                else
                {
                    frontCameraSeq++;
                }
                if (reset)
                {
                    carController.Reset();
                    reset = false;
                }  
            }
            catch (Exception ex)
            {
                Debug.Log(ex.ToString());
                //throw;
            }
        }
    }

    private void setQquality()
    {
        if (frame_time >= target_frame_time) quality -= 3;
        if (frame_time < target_frame_time / 2) quality += 1;
        if (quality < 5) quality = 5;
        else if (quality > maxImageQuality) quality = maxImageQuality;
    }

    private void setHeader(UInt16 seq, UInt16 frag, byte[] frame)
    {
        var seqBytes = getSeqBytes(seq);
        var fragBytes = getSeqBytes(frag);
        frame[0] = seqBytes[0];
        frame[1] = seqBytes[1];
        frame[2] = fragBytes[0];
        frame[3] = fragBytes[1];
    }

    private byte[] getSeqBytes(UInt16 seq)
    {
        var bytes = BitConverter.GetBytes(seq);
        if (BitConverter.IsLittleEndian)
        {
            var temp = bytes[0];
            bytes[0] = bytes[1];
            bytes[1] = temp;
        }
        return bytes;
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
       // SimCameraSender = new IPEndPoint(IPAddress.Parse(SimCameraIP), SimCameraPort);
        udpClient = new UdpClient(ipLocalEndPoint);
        //simCamUdpClient = new UdpClient();
        connected = true;
        udpReceiveThread = new Thread(RunUdpServer);
        udpReceiveThread.Start(udpClient);
    }

    public void Close()
    {
        connected = false;
        received = false;
        udpClient.Close();
    }

    private void RunUdpServer(object obj)
    {
        UdpClient udpClient = (UdpClient)obj;
        remoteSender = new IPEndPoint(IPAddress.Any, 0);

        while (connected)
        {
            try
            {
                byte[] dataIn = udpClient.Receive(ref remoteSender);
                received = true;
                SetCarControl(dataIn);
            }
            catch (Exception)
            {
              //ignore                
            }
            
        }
        udpClient.Close();
    }

    private void SetCarControl(byte[] data)
    {
        try
        {
            string json = Encoding.UTF8.GetString(data, 0, data.Length);
            var control = JsonUtility.FromJson<CarControlData>(json);
            CarRemoteControl.SteeringAngle = control.steering_angle;
            CarRemoteControl.Acceleration = control.throttle;
            frame_time = control.frame_time;
            reset = control.reset;
        }
        catch (Exception e)
        {
            Debug.Log(e.Message);
        }
    }

    private byte[] GetTelemetry()
    {
        /*
        Dictionary<string, string> data = new Dictionary<string, string>();
        data["steering_angle"] = _carController.CurrentSteerAngle.ToString("N4");
        data["throttle"] = _carController.AccelInput.ToString("N4");
        data["speed"] = _carController.CurrentSpeed.ToString("N4");
        data["image"] = Convert.ToBase64String(CameraHelper.CaptureFrame(FrontFacingCamera));
        JSONObject json = new JSONObject(data);
        byte[] dataOut = Encoding.UTF8.GetBytes(json.ToString());
        return dataOut; */
        return CameraHelper.CaptureFrame(FrontFacingCamera, quality);
    }

    private void FragmentAndSendImage(byte[] data, ushort seq, UdpClient udpClient, IPEndPoint sender)
    {
        int size = data.Length;
        var count = (UInt16)((size + (payloadSize - 1)) / (payloadSize));
        var bufferArray = new byte[count][];
        // Debug.Log(count);
        for (var i = 0; i < count; i++)
        {
            //bufferArray[i] = new byte[Math.Min(telemetryPayloadSize, ((size + 1) - (i * payloadSize)))];
            bufferArray[i] = new byte[frameSize];
            setHeader(seq, (UInt16)(count - i), bufferArray[i]);
            for (var j = 0; j < payloadSize && i * payloadSize + j < size; j++)
            {
                bufferArray[i][j + headerSize] = data[(i * payloadSize) + j];
            }
            udpClient.Send(bufferArray[i], bufferArray[i].Length, sender);
        }              
    }
}

[Serializable]
public class CarControlData
{
    public float steering_angle;
    public float throttle;
    public float frame_time;
    public bool reset;
}

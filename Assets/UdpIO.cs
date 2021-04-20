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
    private volatile bool received;
    private Thread udpReceiveThread;
    private const int listenPort = 11000;
    private const int sendPort = 11002;
    IPEndPoint sender;
    //private volatile byte[] telemetry;
    //private volatile byte[][] fragments;

    UdpClient udpClient;
    private const int frameSize = 1100;
    private const int headerSize = 4;
    private const int payloadSize = frameSize - headerSize;

    private UInt16 seq = 0;


    // Use this for initialization
    void Start () {
        Application.targetFrameRate = 30;
        acceleration = 0;
        steeringAngle = 0;
        _carController = CarRemoteControl.GetComponent<CarController>();
        connected = false;
        received = false;
        Connect();
    }

    // Update is called once per frame
    void Update()
    {
        var telemetry = GetTelemetry();        
        if (received && connected && telemetry != null && sender != null)
        {
            try
            {
               // var fragments = FragmentTelemetry(telemetry);
                /*for (int i = 0; i < fragments.Length; i++)
                {
                    udpClient.Send(fragments[i], fragments[i].Length, sender);
                }*/

                int size = telemetry.Length;
                var count = (UInt16)(size + (payloadSize - 1)) / (payloadSize);
                var bufferArray = new byte[count][];
                //Debug.Log(seq);
                for (var i = 0; i < count; i++)
                {
                    //bufferArray[i] = new byte[Math.Min(telemetryPayloadSize, ((size + 1) - (i * payloadSize)))];
                    bufferArray[i] = new byte[frameSize];
                    setHeader(seq, (UInt16)(count - i), bufferArray[i]);
                    for (var j = 0; j < payloadSize && i * payloadSize + j < size; j++)
                    {
                        bufferArray[i][j + headerSize] = telemetry[(i * payloadSize) + j];
                    }
                    udpClient.Send(bufferArray[i], bufferArray[i].Length, sender);
                }
                if(seq >= 65534)
                {
                    seq = 0;
                }
                else
                {
                    seq++;
                }

            }
            catch (Exception ex)
            {
                Debug.Log(ex.ToString());
                //throw;
            }
               

            
        }

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
        if(BitConverter.IsLittleEndian)
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
        udpClient = new UdpClient(ipLocalEndPoint);
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
        sender = new IPEndPoint(IPAddress.Any, 0);

        while (connected)
        {
            byte[] dataIn = udpClient.Receive(ref sender);
            received = true;
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
        /*
        Dictionary<string, string> data = new Dictionary<string, string>();
        data["steering_angle"] = _carController.CurrentSteerAngle.ToString("N4");
        data["throttle"] = _carController.AccelInput.ToString("N4");
        data["speed"] = _carController.CurrentSpeed.ToString("N4");
        data["image"] = Convert.ToBase64String(CameraHelper.CaptureFrame(FrontFacingCamera));
        JSONObject json = new JSONObject(data);
        byte[] dataOut = Encoding.UTF8.GetBytes(json.ToString());
        return dataOut; */
        return CameraHelper.CaptureFrame(FrontFacingCamera);
    }

    private byte[][] FragmentTelemetry(byte[] data)
    {
        int size = data.Length;
        var count = (int) (size + (payloadSize - 1)) / (payloadSize);
        var bufferArray = new byte[count][];
        Debug.Log("Len " + data.Length + " " + count);
        for (var i = 0; i < count; i++)
        {
            bufferArray[i] = new byte[Math.Min(frameSize, ((size+1) - (i * payloadSize)) )];
            bufferArray[i][0] = (byte)i;
            for (var j = 0; j < payloadSize && i * payloadSize + j < size; j++)
            {
               // Debug.Log(i * count + j);                
                bufferArray[i][j+1] = data[(i * count) + j];
            }
        }        
        return bufferArray;
    }
}

[Serializable]
public class CarControlData
{
    public float steering_angle;
    public float throttle;
}

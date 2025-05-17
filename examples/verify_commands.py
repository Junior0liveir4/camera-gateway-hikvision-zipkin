from is_wire.core import Channel, Subscription, Message
from is_msgs.camera_pb2 import CameraConfig, CameraConfigFields, PTZControl
from is_msgs.common_pb2 import FieldSelector
from is_msgs.image_pb2 import Image, Resolution
from google.protobuf.empty_pb2 import Empty
import json
import socket
import time
import os

if __name__ == "__main__":
# -------------------------- Options -------------------------
    '''
    param = 0  : Get information.                                          (AVAILABLE)
    param = 1  : Get/Set changes on channel_id.                             (AVAILABLE)
    param = 2  : Get/Set changes on stream_channel_id (stream_id).          (AVAILABLE)
    param = 3  : Get/Set changes on Image Compression Standart              (NOT AVAILABLE)
    param = 4  : Get/Set changes on resolution.                             (AVAILABLE)
    param = 5  : Get/Set changes on fps.                                    (AVAILABLE)
    param = 6  : Get/Set changes on Camera Position using absolute values.  (AVAILABLE)
    param = 7  : Get/Set changes on Camera Position using steps.            (AVAILABLE)
 
    param = 8  : Get/Set changes on Camera brightness.                      (AVAILABLE)
    param = 9  : Get/Set changes on Camera exposure.                        (NOT POSSIBLE)
    param = 10 : Get/Set changes on Camera focus.                           (NOT POSSIBLE)
    param = 11 : Get/Set changes on Camera gain.                            (NOT POSSIBLE)
    param = 12 : Get/Set changes on Camera gamma.                           (NOT POSSIBLE)
    param = 13 : Get/Set changes on Camera hue.                             (NOT POSSIBLE)
    param = 14 : Get/Set changes on Camera iris.                            (NOT POSSIBLE)
    param = 15 : Get/Set changes on Camera saturation.                      (AVAILABLE)
    param = 16 : Get/Set changes on Camera sharpness.                       (AVAILABLE)
    param = 17 : Get/Set changes on Camera shutter.                         (NOT AVAILABLE)
    param = 18 : Get/Set changes on Camera white_balance_bu.                (AVAILABLE)
    param = 19 : Get/Set changes on Camera white_balance_rv.                (AVAILABLE)
    param = 20 : Get/Set changes on Camera zoom.                            (AVAILABLE)
    '''    
    cont = True
    config_file = './tests_config.json'
    # config_file = '../etc/conf/config.json'
    config = json.load(open(config_file, 'r'))
    cam_id = config["camera"]["id"]
    
    channel = Channel(config["broker_uri"])
    subscription = Subscription(channel)

    while cont:
        os.system('cls' if os.name == 'nt' else 'clear')
        param = int(input('Parametro desejado: '))

    # -------------------------- Init ----------------------------

    # ---------------------- Get First Config --------------------
        selector = FieldSelector(fields=[CameraConfigFields.Value("ALL")])
        topic = "CameraGateway.{}.GetConfig".format(cam_id)
        print(f"Publishing to topic: {topic}")
        channel.publish(
            Message(content=selector, reply_to=subscription),
            topic=topic)
        try:
            reply = channel.consume(timeout=3.0)
            unpacked_msg = reply.unpack(CameraConfig)
            print('RPC Status:', reply.status, '\nReply:', unpacked_msg)
        except socket.timeout:
            print('No reply :(')

    # ---------------------- Set New Config -----------------------

        msg_config = CameraConfig()

        if   param == 1:
            msg_config.channel_id.value = 1           # This camera just works on channel 1.
        elif param == 2:
            msg_config.stream_channel_id.value = 1    # This camera has 3 streams (1, 2 and 3).
        elif param == 3:
            print('This request is not available.')
        elif param == 4:
            # options = [(1920, 1080), (1280, 960), (1280, 720)]
            msg_config.image.resolution.height = 480
            msg_config.image.resolution.width = 704    
        elif param == 5:
            # fps_values = {1, 2, 4, 6, 8, 10, 12, 15, 16, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60}
            msg_config.sampling.frequency.value = 30  # fps value (int).
        elif param == 6: 
            msg_config.ptzcontrol.absolute.x = 0    # Int value, positive or negative.
            msg_config.ptzcontrol.absolute.y = 0    # Int value, HomePosition reference.
            msg_config.ptzcontrol.absolute.z = 0     # Int value, positive or negative.
        elif param == 7:
            msg_config.ptzcontrol.step.x = 2          # Int value, positive or negative.
            msg_config.ptzcontrol.step.y = 0          # Int value, positive or negative.
            msg_config.ptzcontrol.step.z = 0          # Int value, positive or negative.

        elif param == 8:
            msg_config.camera.brightness.ratio = -1.0          # Default is 0.5.
        elif param == 9:
            msg_config.camera.exposure.ratio = 1.0           # Will return a message ERROR.
        elif param == 10:
            msg_config.camera.focus.ratio = 1.0              # Will return a message ERROR. 
        elif param == 11:
            msg_config.camera.gain.ratio = 1.0               # Will return a message ERROR.
        elif param == 12:
            msg_config.camera.gamma.ratio = 1.0              # Will return a message ERROR.
        elif param == 13:
            msg_config.camera.hue.ratio = 1.0                # Will return a message ERROR.  
        elif param == 14:
            msg_config.camera.iris.ratio = 1.0               # Will return a message ERROR.  
        elif param == 15:
            msg_config.camera.saturation.ratio = -0.3          # Default is 0.3.
        elif param == 16:
            msg_config.camera.sharpness.ratio = -0.50          # Default is 0.5. 
        elif param == 17:
            msg_config.camera.shutter.ratio = 1.0            # Will return a message ERROR. 
        elif param == 18:
            msg_config.camera.white_balance_bu.ratio = -0.20   # Default is 0.2. 
        elif param == 19:
            msg_config.camera.white_balance_rv.ratio = -0.20   # Default is 0.2. 
        elif param == 20:
            msg_config.camera.zoom.ratio = -0.1              # 0.0 to 1.0 corespond 10 to 250 on PTZControl Message. 
        else:
            print("No configure setting requested.")
        
        channel.publish(Message(content=msg_config, reply_to=subscription),topic="CameraGateway.{}.SetConfig".format(cam_id))
        try:
            reply = channel.consume(timeout=3.0)
            struct = reply.unpack(Empty)
            print('RPC Status:', reply.status, '\nReply:', struct)
        except socket.timeout:
            print('No reply :(')
        
        time.sleep(2)

    # ---------------------- Get New Config -----------------------
        selector = FieldSelector(fields=[CameraConfigFields.Value("ALL")])
        channel.publish(
            Message(content=selector, reply_to=subscription),
            topic="CameraGateway.{}.GetConfig".format(cam_id))
        try:
            reply = channel.consume(timeout=3.0)
            unpacked_msg = reply.unpack(CameraConfig)
            print('RPC Status:', reply.status, '\nReply:', unpacked_msg)
        except socket.timeout:
            print('No reply :(')
        
        opt = input('Continuar? [y/n] ')
        cont = False if opt == 'n' else True
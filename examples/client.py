from is_wire.core import Channel,Subscription,Message
from is_msgs.image_pb2 import Image
import numpy as np
import cv2
import json
import time


def to_np(input_image):
    if isinstance(input_image, np.ndarray):
        output_image = input_image
    elif isinstance(input_image, Image):
        buffer = np.frombuffer(input_image.data, dtype=np.uint8)
        output_image = cv2.imdecode(buffer, flags=cv2.IMREAD_COLOR)
    else:
        output_image = np.array([], dtype=np.uint8)
    return output_image

if __name__ == '__main__':

    config_file = './tests_config.json'
    # config_file = '../etc/conf/config.json'
    print('---RUNNING EXAMPLE DEMO OF THE CAMERA CLIENT---')

    config = json.load(open(config_file, 'r'))
    
    channel = Channel(config["broker_uri"])
    subscription = Subscription(channel=channel,name="Hikvision_Camera")
    subscription.subscribe(topic='CameraGateway.{}.Frame'.format(config["camera"]["id"]))

    window = f'Hikvision Camera - ID: {config["camera"]["id"]}'
    cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(window, 0, 0)

    while True:
        msg = channel.consume()  
        im = msg.unpack(Image)
        frame = to_np(im)
        
        cv2.imshow(window, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
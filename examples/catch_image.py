import cv2
import json

config_file = './tests_config.json'
# config_file = '../etc/conf/config.json'
config = json.load(open(config_file, 'r'))

camera_config = config['camera']

camera_id = camera_config['id']
ip = camera_config["ip"]
username = camera_config["username"]
password = camera_config["password"]
http_port = camera_config["http_port"]
rtsp_port = camera_config["rtsp_port"]
channel_id = camera_config["stream"]["channel_id"]
stream_id = camera_config["stream"]["stream_id"]
base_url = "{}:{}@{}".format(username, password, ip)
cap = cv2.VideoCapture()
cap.open("rtsp://{}:{}/Streaming/Channels/0{}0{}".format(base_url, rtsp_port, channel_id, stream_id))

while(True):
     # Capture frame-by-frame
    ret, frame = cap.read()

    # Our operations on the frame come here
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Display the resulting frame
    cv2.imshow('frame',frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
from is_wire.core import Logger, Status ,StatusCode, logger
from is_msgs.image_pb2 import Image, Resolution, ImageFormat, ImageFormats
from is_msgs.camera_pb2 import PTZControl, CameraSettings
from is_msgs.common_pb2 import Position
import cv2
import time
import queue
import threading
import requests
import xmltodict, json
from enum import Enum

def assert_type(instance, _type, name):
    if not isinstance(instance, _type):
        raise TypeError("Object {} must be of type {}".format(
            name, _type.DESCRIPTOR.full_name))

class Parameters(Enum):
    STREAM_ID = 1
    COMPRESS_STANDART = 2
    RESOLUTION = 3
    FPS = 4


class VideoCapture:
    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)
        self.run = True
        self.q = queue.Queue()
        self.t = threading.Thread(target=self._reader, daemon=True)
        self.t.start()

    def _reader(self):
        while self.run:
            self.cap.grab()
            ret, frame = self.cap.retrieve()
            if not ret:
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)
    
    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        return True, self.q.get()

    def release(self):
        self.run = False
        self.t.join()
        self.cap.release()

class HikvisionDriver(object):
    logger = Logger("HikvisionDriver")

# -=-=-=-=-=-=-=-=-=-=-= INITIALIZATION FUNCTIONS =-=-=-=-=-=-=-=-=-=-=-
    def __init__(self, config, zipkin_url=None):
        self.zipkin_url = zipkin_url
        self.camera_id = config['id']
        self.ip = config["ip"]
        self.username = config["username"]
        self.password = config["password"]
        self.rtsp_port = config["rtsp_port"]
        self.http_port = config["http_port"]
        self.base_url = "{}:{}@{}".format(self.username, self.password, self.ip)

        self.channel_id = config["stream"]["channel_id"]
        self.stream_id = config["stream"]["stream_id"]
        self.compress_standart = config["stream"]["compress_standart"]
        self.resolution = Resolution()
        self.resolution.width = config["stream"]["width"]
        self.resolution.height = config["stream"]["height"]
        self.fps = config["stream"]["fps"]

        image_format = ImageFormat()
        image_format.format = ImageFormats.Value(config["image"]["format"])
        image_format.compression.value = config["image"]["compression"]
        self.set_image_format(image_format)
        status_open_stream = self._open_stream()
        if status_open_stream != Status(StatusCode.OK):
            self.logger.critical("ERROR on camera stream initialization.")
        self.cam_position = Position()       
        self.call_HomePosition()
        while (self.cam_position.x != 0 and self.cam_position.y != 0):
            time.sleep(1)
        
    def _open_stream(self):
        if hasattr(self,'video_capture'):
            self.__del__()
        url = 'rtsp://{}:{}/Streaming/Channels/0{}0{}'.format(self.base_url,self.rtsp_port ,str(self.channel_id), self.stream_id)
        retry = 1
        max_retry = 5
        while retry <= max_retry:
            self.logger.info("Connecting to camera {} ({}:{})".format(self.camera_id,self.ip,self.rtsp_port))
            self.video_capture = VideoCapture(url)
            if self.video_capture.isOpened():
                break
            else:          
                self.logger.error("Not conntected to camera {} ({}:{}). Retrying {}/{}...".format(self.camera_id,self.ip,self.rtsp_port,retry,max_retry))
                retry += 1
        else:
            self.logger.error("Max number of connection retries have been reached.")
            return Status(StatusCode.DEADLINE_EXCEEDED,why="Max number of connection retries have been reached.")
        self.logger.info("Camera {} ({}:{}) connected.".format(self.camera_id,self.ip,self.rtsp_port))
        self._stream_configuration()
        return Status(StatusCode.OK)    
    
    def _stream_configuration(self): 
        xml = "<Video>\r\n<enabled>true</enabled>\r\n<videoInputChannelID>1</videoInputChannelID>\r\n"
        xml += "<videoCodecType>{}</videoCodecType>\r\n".format(self.compress_standart)
        xml += "<videoScanType>progressive</videoScanType>\r\n"
        xml += "<videoResolutionWidth>{}</videoResolutionWidth>\r\n".format(self.resolution.width)
        xml += "<videoResolutionHeight>{}</videoResolutionHeight>\r\n".format(self.resolution.height)
        xml += "<videoQualityControlType>VBR</videoQualityControlType>\r\n<constantBitRate>4096</constantBitRate>\r\n"
        xml += "<fixedQuality>60</fixedQuality>\r\n"
        xml += "<maxFrameRate>{}</maxFrameRate>\r\n".format(int(self.fps*100)) 
        xml += "<keyFrameInterval>50</keyFrameInterval>\r\n<BPFrameInterval>0</BPFrameInterval>\r\n"
        xml += "<snapShotImageType>JPEG</snapShotImageType>\r\n<SVC>\r\n<enabled>false</enabled>\r\n</SVC>\r\n</Video>\r\n"
        url = 'http://{}:{}/Streaming/channels/0{}0{}'.format(self.base_url, self.http_port, self.channel_id, self.stream_id)
        return requests.put(url, data=xml)
    
    def sinc_cam_status(self, param): 
        url = 'http://{}:{}/Streaming/channels/0{}0{}'.format(self.base_url, self.http_port, self.channel_id, self.stream_id)
        request = requests.get(url)
        status = xmltodict.parse(request.text)
        status_json = json.loads(json.dumps(status))
        if param == Parameters.STREAM_ID: self.stream_id = int(str(status_json['StreamingChannel']['id'])[2]) 
        elif param == Parameters.COMPRESS_STANDART: self.compress_standart = status_json['StreamingChannel']['Video']['videoCodecType']
        elif param == Parameters.RESOLUTION: 
            self.resolution.width = int(status_json['StreamingChannel']['Video']['videoResolutionWidth'])
            self.resolution.height = int(status_json['StreamingChannel']['Video']['videoResolutionHeight']) 
        elif param == Parameters.FPS: self.fps = float(status_json['StreamingChannel']['Video']['maxFrameRate'])/100

        else: self.logger.error('Error in camera synchronization. Consult camera drive Parameters class to know more.')

# -=-=-=-=-=-=-=-=-=-=-=-=-=-= GET FUNCTIONS =-=-=-=-=-=-=-=-=-=-=-=-=-=-            
    def get_channel_id(self): 
        return self.channel_id

    def get_stream_id(self): 
        param = Parameters.STREAM_ID
        self.sinc_cam_status(param)
        return self.stream_id

    def get_compress_standart(self):
        param = Parameters.COMPRESS_STANDART
        self.sinc_cam_status(param)
        return self.compress_standart

    def get_image_format(self):
        image_format = ImageFormat()
        if self.encode_format == ".jpeg":
            image_format.format = ImageFormats.Value("JPEG")
            image_format.compression.value = self.encode_parameters[1] / 100.0
        elif self.encode_format == ".png":
            image_format.format = ImageFormats.Value("PNG")
            image_format.compression.value = self.encode_parameters[1] / 9.0
        elif self.encode_format == ".webp":
            image_format.format = ImageFormats.Value("WebP")
            image_format.compression.value = (
                self.encode_parameters[1] - 1) / 99.0
        return image_format

    def get_fps(self): 
        param = Parameters.FPS
        self.sinc_cam_status(param)
        return (self.fps)

    def get_resolution(self): 
        param = Parameters.RESOLUTION
        self.sinc_cam_status(param)
        return self.resolution

    def get_np_image(self):
        _, frame = self.video_capture.read()
        return frame    

    def get_position(self): 
        url = 'http://{}:{}/PTZCtrl/channels/{}/status'.format(self.base_url,self.http_port ,self.channel_id)
        request = requests.get(url)
        status = xmltodict.parse(request.text)
        status_json = json.loads(json.dumps(status))
        self.cam_position.x = int(status_json['PTZStatus']['AbsoluteHigh']['azimuth'])        
        self.cam_position.y = int(status_json['PTZStatus']['AbsoluteHigh']['elevation'])
        self.cam_position.z = int(status_json['PTZStatus']['AbsoluteHigh']['absoluteZoom'])
        reply = PTZControl()
        reply.absolute.CopyFrom(self.cam_position)
        return reply

    def get_pl_frequency(self): 
        # Power line frequency: Brazil = 60Hz.
        request_power_frequency = requests.get('http://{}:{}/Image/channels/{}/powerLineFrequency'.format(self.base_url, self.http_port ,self.channel_id))
        status = xmltodict.parse(request_power_frequency.text)
        status_json = json.loads(json.dumps(status))
        pl_frequency = status_json['powerLineFrequency']['powerLineFrequencyMode']
        return pl_frequency

    def get_brightness(self):
        request_brightness = requests.get('http://{}:{}/Image/channels/{}/Color'.format(self.base_url,self.http_port,self.channel_id))
        status = xmltodict.parse(request_brightness.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.brightness.ratio = float(status_json['Color']['brightnessLevel'])/100
        return reply.brightness

    def get_gain(self):
        request_gain = requests.get('http://{}:{}/Image/channels/{}/Gain'.format(self.base_url, self.http_port ,self.channel_id))
        status = xmltodict.parse(request_gain.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.gain.ratio = float(status_json['Gain']['GainLevel'])/100
        return reply.gain

    def get_saturation(self):
        request_saturation = requests.get('http://{}:{}/Image/channels/{}/Color'.format(self.base_url,self.http_port,self.channel_id))
        status = xmltodict.parse(request_saturation.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.saturation.ratio = float(status_json['Color']['saturationLevel'])/100
        return reply.saturation

    def get_sharpness(self):
        request_sharpness = requests.get('http://{}:{}/Image/channels/{}/Sharpness'.format(self.base_url,self.http_port,self.channel_id))
        status = xmltodict.parse(request_sharpness.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.sharpness.ratio = float(status_json['Sharpness']['SharpnessLevel'])/100
        return reply.sharpness

    def get_white_balance_bu(self):
        request_white_balance_bu = requests.get('http://{}:{}/Image/channels/{}/WhiteBlance'.format(self.base_url,self.http_port,self.channel_id))
        status = xmltodict.parse(request_white_balance_bu.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.white_balance_bu.ratio = float(status_json['WhiteBlance']['WhiteBlanceBlue'])/100
        return reply.white_balance_bu

    def get_white_balance_rv(self):
        request_white_balance_rv = requests.get('http://{}:{}/Image/channels/{}/WhiteBlance'.format(self.base_url,self.http_port,self.channel_id))
        status = xmltodict.parse(request_white_balance_rv.text)
        status_json = json.loads(json.dumps(status))
        reply = CameraSettings()
        reply.white_balance_rv.ratio = float(status_json['WhiteBlance']['WhiteBlanceRed'])/100
        return reply.white_balance_rv

    def get_zoom(self):
        url = 'http://{}:{}/PTZCtrl/channels/{}/status'.format(self.base_url,self.http_port ,self.channel_id)
        request = requests.get(url)
        status = xmltodict.parse(request.text)
        status_json = json.loads(json.dumps(status))
        self.cam_position.z = int(status_json['PTZStatus']['AbsoluteHigh']['absoluteZoom'])
        zoom = float(self.cam_position.z - 10)/240 # Zoom's values are 10 to 250 (PTZControl)
        reply = CameraSettings()
        reply.zoom.ratio = zoom
        return reply.zoom

# -=-=-=-=-=-=-=-=-=-=-=-=-=-= SET FUNCTIONS =-=-=-=-=-=-=-=-=-=-=-=-=-=-            
    def set_channel(self, channel_id): 
        channels = [1] # This camera works just at channel 1.
        if channel_id in channels:
            self.channel_id = channel_id
            self._open_stream()
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT,
                why="Unsupported channel value! Received: {} | Supported: {}".format(channel_id,list(channels)))

    def set_stream_id(self, stream_id): 
        streams = [1, 2, 3] # The HIKVISION camera has 3 streams.
        if stream_id in streams:
            self.logger.info("Setting the new stream_id = {}.".format(stream_id))
            self.stream_id = stream_id
            return self._open_stream()
        else:
            return Status(StatusCode.INVALID_ARGUMENT,
                   why="Unsupported stream value! Received: {} | Supported: {}".format(stream_id, list(streams)))

    def set_compress_standart(self, compress_standart):
        stream_id = self.get_stream_id()
        compress_list = []
        if stream_id == 1:
            compress_list = ['H.265+','H.265','H.264+','H.264']
            if compress_standart in compress_list: return self._open_stream()
        elif stream_id == 2 or stream_id == 3:
            compress_list = ['H.265','H.264','MJPEG']
            if compress_standart in compress_list: return self._open_stream()
        else:
            return Status(StatusCode.INVALID_ARGUMENT, 
                   why="This Compress Standart is not supported by the Stream! Received: {} | Supported: {}".format(compress_standart,list(compress_list)))

    def set_image_format(self, image_format):
        assert_type(image_format, ImageFormat, "image_format")
        if image_format.format == ImageFormats.Value("JPEG"):
            self.encode_format = ".jpeg"
        elif image_format.format == ImageFormats.Value("PNG"):
            self.encode_format = ".png"
        elif image_format.format == ImageFormats.Value("WebP"):
            self.encode_format = ".webp"
        else:
            return Status(StatusCode.NOT_FOUND, why="Image Format not found or unsupported")
            

        if image_format.HasField("compression"):
            if self.encode_format == '.jpeg':
                self.encode_parameters = [
                    cv2.IMWRITE_JPEG_QUALITY,
                    int(image_format.compression.value * (100 - 0) + 0)
                ]
            elif self.encode_format == '.png':
                self.encode_parameters = [
                    cv2.IMWRITE_PNG_COMPRESSION,
                    int(image_format.compression.value * (9 - 0) + 0)
                ]
            elif self.encode_format == '.webp':
                self.encode_parameters = [
                    cv2.IMWRITE_WEBP_QUALITY,
                    int(image_format.compression.value * (100 - 1) + 1)
                ]
            else:
                return Status(StatusCode.NOT_FOUND, why="Image Compression not found or unsupported")
        return Status(StatusCode.OK)
  
    def set_fps(self, fps):
        # There are others options: 1/16 , 1/8, 1/4, 1/2.
        fps_values = {1, 2, 4, 6, 8, 10, 12, 15, 16, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60}
        if fps in fps_values:
            if fps == self.fps: return Status(StatusCode.INVALID_ARGUMENT, why="The chosen fps value is already setted.")
            self.fps = fps
            return self._open_stream()
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported FPS value! Received: {} | Supported: {}".format(fps, list(fps_values)))

    def set_resolution(self, resolution): 
        stream_id = self.get_stream_id()
        pl_frequency = self.get_pl_frequency()
        fps = self.get_fps()

        freq = (resolution.width, resolution.height)
        if stream_id == 1:
            if pl_frequency == '50hz':
                '50Hz: 25fps (1920 × 1080, 1280 × 960, 1280 × 720),50fps (1920 × 1080, 1280 × 960, 1280 × 720)'
                return Status(StatusCode.INVALID_ARGUMENT, \
                        why="That Driver was not build to run on 50Hz of power line frequency, \
                        please consider build another feature.")
            elif pl_frequency == '60hz':
                if fps == 30:
                    options = [(1920, 1080), (1280, 960), (1280, 720)]
                    if freq in options:
                        self.resolution.width  = resolution.width
                        self.resolution.height = resolution.height
                        return self._open_stream()
                    else:
                        return Status(StatusCode.INVALID_ARGUMENT, \
                        why="Unsupported resolution values! Received: {} | Supported: {}".format(resolution,list(options)))
                elif fps == 60:
                    options = [(1920, 1080), (1280, 960), (1280, 720)]
                    if freq in options:
                        self.resolution.width  = resolution.width
                        self.resolution.height = resolution.height
                        return self._open_stream()
                    else:
                        return Status(StatusCode.INVALID_ARGUMENT, \
                        why="Unsupported resolution values! Received: {} | Supported: {}".format(resolution,list(options)))
        elif stream_id == 2:
            if pl_frequency == '50hz':
                '50Hz: 25fps (704 × 576, 640 × 480, 352 × 288)'
                return Status(StatusCode.INVALID_ARGUMENT, \
                        why="That Driver was not build to run on 50Hz of power line frequency, \
                        please consider build another feature.")
            elif pl_frequency == '60hz':
                if fps == 30:
                    options = [(1704, 480), (640, 480), (352, 240)]
                    if freq in options:
                        self.resolution.width  = resolution.width
                        self.resolution.height = resolution.height
                        return self._open_stream()
                    else:
                        return Status(StatusCode.INVALID_ARGUMENT, \
                        why="Unsupported resolution values! Received: {} | Supported: {}".format(resolution,list(options)))                
                else:
                    return Status(StatusCode.INVALID_ARGUMENT, \
                    why="Unsupported fps value! Actual: {} | Supported: 30".format(fps,))
        elif stream_id == 3:
            if pl_frequency == '50hz':
                '50Hz: 25fps (1920 × 1080, 1280 × 960, 1280 × 720, 704 × 576, 640 × 480, 352 × 288)'
                return Status(StatusCode.INVALID_ARGUMENT, \
                        why="That Driver was not build to run on 50Hz of power line frequency, \
                        please consider build another feature.")
            elif pl_frequency == '60hz':
                if fps == 30:
                    options = [(1920, 1080), (1280, 960), (1280, 720), (704, 480), (640, 480), (352, 240)]
                    if freq in options:
                        self.resolution.width  = resolution.width
                        self.resolution.height = resolution.height
                        return self._open_stream()
                    else:
                        return Status(StatusCode.INVALID_ARGUMENT, \
                        why="Unsupported resolution values! Received: {} | Supported: {}".format(resolution,list(options)))                
                else:
                    return Status(StatusCode.INVALID_ARGUMENT, \
                    why="Unsupported fps value! Actual: {} | Supported: 30".format(fps,))
        else:
            return Status(StatusCode.ERROR, 
                   why="Something wrong happened when you try to set a new resolution, the stream_id wasn't recognised.")           

    def set_position(self, ptzcontrol):
        elevation = int(self.cam_position.y)
        azimuth =   int(self.cam_position.x)
        abs_zoom =  int(self.cam_position.z)
        
        position = Position()
    
        # Step Moviment:
        if ptzcontrol.HasField("step"):
            position = ptzcontrol.step

            azimuth_step =   int(position.x) * 50 # position.x 1 step value
            elevation_step = int(position.y) * 50 # position.y 1 step value
            zoom_step =      int(position.z) * 10 # position.z 1 step value

            if (azimuth + azimuth_step) < 0: azimuth = 3600 + (azimuth + azimuth_step)
            elif (azimuth + azimuth_step) > 3600: azimuth = (azimuth + azimuth_step) - 3600
            else: azimuth += azimuth_step

            elevation = elevation + elevation_step
            abs_zoom = abs_zoom + zoom_step
        
        # Absolute Moviment:
        elif  ptzcontrol.HasField('absolute'):
            position = ptzcontrol.absolute

            elevation = int(position.y)
            azimuth = int(position.x)
            abs_zoom = int(position.z)

            if azimuth < 0: azimuth = 3600 + azimuth
            elif azimuth > 3600: azimuth = azimuth - 3600

        else:
            return Status(StatusCode.INVALID_ARGUMENT, 
                   why="The message request contains a different format than expected to hikvision camera gateway, consider update the driver for new options of moviment in PTZControl or try another option like absolute or step.")

        # Request to camera
        if (elevation, azimuth, abs_zoom) != (int(self.cam_position.y), int(self.cam_position.x), int(self.cam_position.z)):
            xml = "<PTZData version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n<AbsoluteHigh>\r\n"
            xml += "<elevation>{}</elevation>\r\n".format(str(elevation))
            xml += "<azimuth>{}</azimuth>\r\n".format(str(azimuth))
            xml += "<absoluteZoom>{}</absoluteZoom>\r\n".format(str(abs_zoom))
            xml += "</AbsoluteHigh>\r\n</PTZData>"

            url = 'http://{}:{}/PTZCtrl/channels/{}/absolute'.format(self.base_url,self.http_port ,self.channel_id)
            reply = None 
            request = requests.put(url, data=xml)

            while reply != 'OK':
                status = xmltodict.parse(request.text)
                status_json = json.loads(json.dumps(status))
                reply = status_json['ResponseStatus']['statusString']

            if reply == 'OK':
                return Status(StatusCode.OK)
            else:
                return Status(StatusCode.INTERNAL_ERROR, 
                       why="Set_Position failed! Received: {}".format(position))
        
        else:
            return Status(StatusCode.INVALID_ARGUMENT, 
                   why="Unsupported value! You may selected the actual position.")

    def set_brightness(self, brightness):
        if brightness >= 0 and brightness<=1.0:
            brightness = int(brightness*100)
            url =  'http://{}:{}/Image/channels/{}/Color'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<Color version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<brightnessLevel>{}</brightnessLevel>\r\n".format(brightness) 
            xml += "</Color>\r\n"
            request_brightness = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported brightness value! Received: {} | Supported: 0.0 to 1.0)".format(brightness))

    def set_exposure(self, exposure):       
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support exposure changes.")
                   
    def set_focus(self, focus):
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support focus changes.")

    def set_gain(self, gain):
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support gain changes.")

    def set_gamma(self, gamma):
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support gamma changes.")

    def set_hue(self, hue):
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support hue changes.")
    
    def set_iris(self, iris):
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support iris changes.")

    def set_saturation(self, saturation):
        if saturation >= 0 and saturation<=1.0:
            saturation = int(saturation*100)
            url =  'http://{}:{}/Image/channels/{}/Color'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<Color version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<saturationLevel>{}</saturationLevel>\r\n".format(saturation) 
            xml += "</Color>\r\n"
            request_saturation = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported saturation value! Received: {} | Supported: 0.0 to 1.0)".format(saturation))
    
    def set_sharpness(self, sharpness):
        if sharpness >= 0 and sharpness<=1.0:
            sharpness = int(sharpness*100)
            url =  'http://{}:{}/Image/channels/{}/Sharpness'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<Sharpness version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<SharpnessLevel>{}</SharpnessLevel>\r\n".format(sharpness) 
            xml += "</Sharpness>\r\n"
            request_sharpness = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported sharpness value! Received: {} | Supported: 0.0 to 1.0)".format(sharpness))
  
    def set_shutter(self, shutter):
        '''
        if shutter >= 0 and shutter<=1.0:
            shutter = int(shutter*100)
            url =  'http://{}:{}/Image/channels/{}/Shutter'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<Shutter version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<ShutterLevel>{}</ShutterLevel>\r\n".format(shutter) 
            xml += "</Shutter>\r\n"
            request_shutter = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported shutter value! Received: {} | Supported: 0.0 to 1.0)".format(saturation))
        '''
        return Status(StatusCode.CANCELLED, 
                   why="This camera doesn't support shutter changes.")
    
    def set_white_balance_bu(self, white_balance_bu):
        if white_balance_bu >= 0 and white_balance_bu<=1.0:
            white_balance_bu = int(white_balance_bu*100)
            url =  'http://{}:{}/Image/channels/{}/WhiteBlance'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<WhiteBlance version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<WhiteBlanceStyle>auto</WhiteBlanceStyle>\r\n"
            xml += "<WhiteBlanceBlue>{}</WhiteBlanceBlue>\r\n".format(white_balance_bu) 
            xml += "</WhiteBlance>\r\n"
            request_white_balance_bu = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported white_balance_bu value! Received: {} | Supported: 0.0 to 1.0)".format(white_balance_bu))

    def set_white_balance_rv(self, white_balance_rv):
        if white_balance_rv >= 0 and white_balance_rv<=1.0:
            white_balance_rv = int(white_balance_rv*100)
            url =  'http://{}:{}/Image/channels/{}/WhiteBlance'.format(self.base_url,self.http_port,self.channel_id)
            xml =  "<WhiteBlance version=\"1.0\" xmlns=\"http://www.hikvision.com/ver10/XMLSchema\">\r\n"
            xml += "<WhiteBlanceStyle>auto</WhiteBlanceStyle>\r\n"
            xml += "<WhiteBlanceRed>{}</WhiteBlanceRed>\r\n".format(white_balance_rv) 
            xml += "</WhiteBlance>\r\n"
            request_white_balance_rv = requests.put(url, data=xml)
            return Status(StatusCode.OK)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported white_balance_rv value! Received: {} | Supported: 0.0 to 1.0)".format(white_balance_rv))

    def set_zoom(self, zoom):
        if zoom >= 0 and zoom<=1.0:
            zoom = int(zoom*240 + 10) # 0.0 to 1.0 as 10 to 240 on PTZControl Message.
            ptzcontrol = PTZControl()
            ptzcontrol.absolute.x = self.cam_position.x
            ptzcontrol.absolute.y = self.cam_position.y
            ptzcontrol.absolute.z = zoom
            return self.set_position(ptzcontrol)
        else:
            return Status(StatusCode.INVALID_ARGUMENT, why="Unsupported zoom value! Received: {} | Supported: 0.0 to 1.0)".format(zoom))

# -=-=-=-=-=-=-=-=-=-=-=-=-= OTHERS FUNCTIONS =-=-=-=-=-=-=-=-=-=-=-=-=-            
    def grab_image(self):
        frame = self.get_np_image()
        image = cv2.imencode(ext=self.encode_format,
                             img=frame, params=self.encode_parameters)
        return Image(data=image[1].tobytes())

    def __del__(self):
        if hasattr(self,'video_capture'):
            self.logger.info("Disconnecting from video capture")
            self.video_capture.release()

    def call_HomePosition(self): 
        url = 'http://{}:{}/PTZCtrl/channels/1/homeposition/goto'.format(self.base_url,self.http_port)
        request = requests.put(url)
        self.cam_position.x = 0
        self.cam_position.y = 0
        self.logger.info("Calling home Position.")
        return Status(StatusCode.OK)

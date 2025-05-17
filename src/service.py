import json
import sys
from camera_driver.hikvision import HikvisionDriver
from camera_gateway.gateway import CameraGateway


def main():
    config_file = sys.argv[1] if len(sys.argv) > 1 else '../etc/conf/config.json'
    config = json.load(open(config_file, 'r'))

    broker_uri = config['broker_uri']
    camera_config = config['camera']

    driver = HikvisionDriver(camera_config, zipkin_url=config.get('zipkin_url'))

    service = CameraGateway(driver=driver)
    service.run(broker_uri=broker_uri)

if __name__ == "__main__":
    main()

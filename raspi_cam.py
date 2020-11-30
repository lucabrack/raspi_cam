import cv2
import argparse
import os
import numpy as np
from picamera.array import PiRGBArray
from picamera import PiCamera
import time
from time import sleep
from configparser import ConfigParser

parser = argparse.ArgumentParser(description="Control Raspi Cam")
parser.add_argument("-pv", "--preview_video", action="store_true",
                    help="Preview Camera Input as Video Stream in small window. Kill with 'q'")
parser.add_argument("-ps", "--preview_still", action="store_true",
                    help="Preview Camera Input as Still Image in window. Kill with any Keyboard Input. Press 's' to save image")
parser.add_argument("-tl", "--time_lapse", type=int,
                    help="Start Timelapse, give Time Intervall in seconds.")
parser.add_argument("-t", "--time", type=int, default=0,
                    help="Time 'till preview or timelapse gets killed in seconds")
parser.add_argument("-d", "--delay", type=int, default=0,
                    help="Delay the start of a timelapse in seconds.")
parser.add_argument("-f", "--fixed_parameter", action="store_true",
                    help="Shutter Speed and Auto White Balancing are set to a fix parameter. Helps with Timelapse. Capturing Images takes significantly longer.")
parser.add_argument("-o", "--output", action="store_true",
                    help="Store Image. Either the last one of a preview or a new one without Preview.")
args = parser.parse_args()

image = None

def init_camera(fixed=args.fixed_parameter):
    print("Initialize Camera")
    config = ConfigParser()
    config.read('config.ini')
    
    camera_config = dict(config.items('camera_parameters'))

    if fixed:
        with PiCamera() as camera:
            # Set ISO to the desired value
            camera.iso = int(camera_config['iso'])
            # Wait for the automatic gain control to settle
            sleep(2)
            # Now fix the values to have equal results in all images
            shutter_speed = camera.exposure_speed
            camera.shutter_speed = shutter_speed
            camera.exposure_mode = 'off'
            g = camera.awb_gains
            camera.awb_mode = 'off'
            camera.awb_gains = g
                
            camera_config['shutter_speed'] = shutter_speed
            camera_config['awb_gains'] = g
        
        sleep(0.1)

    return camera_config

def open_camera(camera_config, video=False, fixed=args.fixed_parameter):
    if video:
        w = int(camera_config['vid_width'])
        h = int(camera_config['vid_height'])
    else:
        w = int(camera_config['frame_width'])
        h = int(camera_config['frame_height'])
    resolution = (w,h)

    camera = PiCamera(resolution=resolution, framerate=int(camera_config['frame_rate']))

    if fixed:
        camera.iso = int(camera_config['iso'])
        sleep(2)
        camera.shutter_speed = int(camera_config['shutter_speed'])
        camera.exposure_mode = 'off'
        camera.awb_mode = 'off'
        camera.awb_gains = camera_config['awb_gains']
    
    sleep(0.1)
    
    return camera


def capture_image(camera):
    rawCapture = PiRGBArray(camera)
    camera.capture(rawCapture, format="bgr")
    return rawCapture.array


def save_image(image, timelapse_folder_path=None):
    date_str = time.strftime("%Y_%m_%d")
    time_str = time.strftime("%Y_%m_%d-%H_%M_%S")

    if timelapse_folder_path is None:
        folder_path = os.path.join('images', date_str)
    else:
        folder_path = os.path.join('images', timelapse_folder_path)
    file_path = os.path.join(folder_path, time_str + ".png")

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    success = cv2.imwrite(file_path, image)
    if success:
        print("Image was saved to " + file_path)
    else:
        print("Could not save Image")


def create_timelapse_folder_path():
    time_str = time.strftime("%Y_%m_%d-%H_%M")
    return time_str + '_Timelapse'

def resize_image_for_preview(image, camera_config):
    w = int(camera_config['preview_width'])
    h = int(camera_config['preview_height'])
    resolution = (w,h)
    return cv2.resize(image, resolution)
    
def delay_program(delay, intervall=3):
    start_time = time.time()
    while True:
        if time.time()-start_time > delay:
            break
        sleep(intervall)


if args.preview_video:
    camera_config = init_camera()

    # If time is given start a Timer
    start_time = 0
    if args.time > 0:
        start_time = time.time()

    print("Starting Preview")
    with open_camera(camera_config, video=True) as camera:
        rawCapture = PiRGBArray(camera)
        
        for frame in camera.capture_continuous(rawCapture, format='bgr', use_video_port=True):
            image = frame.array
            
            cv2.imshow("Preview Video",
                        resize_image_for_preview(image, camera_config))
            key = cv2.waitKey(1) & 0xFF
            
            rawCapture.truncate(0)
            
            if key == ord('q'):
                break
            
            if args.time > 0:
                if time.time() - start_time > args.time + 2.0:
                    break
        
if args.preview_still:
    camera_config = init_camera()
    with open_camera(camera_config) as camera:
        image = capture_image(camera)
    
    cv2.imshow("Preview Still",
                resize_image_for_preview(image, camera_config))
    key = cv2.waitKey(args.time*1000) & 0xFF

    if key == ord('s'):
        save_image(image)    


if args.time_lapse is not None:
    delay_program(args.delay)
    camera_config = init_camera()
    tl_folder_path = create_timelapse_folder_path()

    start_time = 0
    if args.time > 0:
        start_time = time.time()

    while True:
        with open_camera(camera_config) as camera:
            image = capture_image(camera)
        
        save_image(image, timelapse_folder_path=tl_folder_path)

        cv2.destroyAllWindows()
        cv2.imshow(time.strftime("%Y_%m_%d-%H_%M_%S"),
                   resize_image_for_preview(image, camera_config))
        key = cv2.waitKey(500) & 0xFF

        if args.time > 0:
            if time.time() - start_time > args.time + 2.0:
                break
        
        time.sleep(args.time_lapse)
    


if args.output:
    if image is None:
        with open_camera(init_camera()) as camera:
            image = capture_image(camera)

    save_image(image)

print('Terminating Program')
cv2.destroyAllWindows()
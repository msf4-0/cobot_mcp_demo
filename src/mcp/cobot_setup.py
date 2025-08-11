#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2022, UFACTORY, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.wen@ufactory.cc> <vinman.cub@gmail.com>

"""
# Notice
#   1. Changes to this file on Studio will not be preserved
#   2. The next conversion will overwrite the file with the same name
# 
# xArm-Python-SDK: https://github.com/xArm-Developer/xArm-Python-SDK
#   1. git clone git@github.com:xArm-Developer/xArm-Python-SDK.git
#   2. cd xArm-Python-SDK
#   3. python setup.py install
"""
import sys
import math
import time
import queue
import datetime
import random
import traceback
import threading
from xarm import version
from xarm.wrapper import XArmAPI

# Coordinates of scan position
SCAN_X = 200
SCAN_Y = 0
SCAN_Z = 300

class RobotMain(object):
    """Robot Main Class"""
    def __init__(self, robot, **kwargs):
        self.alive = True
        self._arm = robot
        self._tcp_speed = 100
        self._tcp_acc = 2000
        self._angle_speed = 20
        self._angle_acc = 500
        self._vars = {}
        self._funcs = {}
        self._robot_init()

    # Robot init
    def _robot_init(self):
        self._arm.clean_warn()
        self._arm.clean_error()
        self._arm.motion_enable(True)
        self._arm.set_mode(0)
        self._arm.set_state(0)
        time.sleep(1)
        self._arm.register_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.register_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'register_count_changed_callback'):
            self._arm.register_count_changed_callback(self._count_changed_callback)

    # Register error/warn changed callback
    def _error_warn_changed_callback(self, data):
        if data and data['error_code'] != 0:
            self.alive = False
            self.pprint('err={}, quit'.format(data['error_code']))
            self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)

    # Register state changed callback
    def _state_changed_callback(self, data):
        if data and data['state'] == 4:
            self.alive = False
            self.pprint('state=4, quit')
            self._arm.release_state_changed_callback(self._state_changed_callback)

    # Register count changed callback
    def _count_changed_callback(self, data):
        if self.is_alive:
            self.pprint('counter val: {}'.format(data['count']))

    def _check_code(self, code, label):
        if not self.is_alive or code != 0:
            self.alive = False
            ret1 = self._arm.get_state()
            ret2 = self._arm.get_err_warn_code()
            self.pprint('{}, code={}, connected={}, state={}, error={}, ret1={}. ret2={}'.format(label, code, self._arm.connected, self._arm.state, self._arm.error_code, ret1, ret2))
        return self.is_alive

    @staticmethod
    def pprint(*args, **kwargs):
        try:
            stack_tuple = traceback.extract_stack(limit=2)[0]
            print('[{}][{}] {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), stack_tuple[1], ' '.join(map(str, args))))
        except:
            print(*args, **kwargs)

    @property
    def arm(self):
        return self._arm

    @property
    def VARS(self):
        return self._vars

    @property
    def FUNCS(self):
        return self._funcs

    @property
    def is_alive(self):
        if self.alive and self._arm.connected and self._arm.error_code == 0:
            if self._arm.state == 5:
                cnt = 0
                while self._arm.state == 5 and cnt < 5:
                    cnt += 1
                    time.sleep(0.1)
            return self._arm.state < 4
        else:
            return False

    def get_cobot_position(self):
        code, pos = self._arm.get_position(is_radian=False)
        return (pos[0], pos[1], pos[2]) if code == 0 else (0.0, 0.0, 0.0)

    # Move in a square
    def move_square(self):
        try:
            self._tcp_speed = 100
            self._arm.move_gohome()
            code = self._arm.set_tool_position(*[0.0, 100.0, 0.0, 0.0, 0.0, 45.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
            code = self._arm.set_tool_position(*[70.71, -70.71, 0.0, 0.0, 0.0, -45.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
            code = self._arm.set_tool_position(*[0.0, -100.0, 0.0, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
            code = self._arm.set_tool_position(*[-100.0, 0.0, 0.0, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
            time.sleep(0.1)
            self._arm.move_gohome()
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)

    # Move in a circle
    def move_circle(self):
        try:
            ''' Code below moves the cobot to a new position and draws a small circle '''
            code = self._arm.set_position(*[200.0, 0.0, 200.0, 180.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, radius=0.0, wait=False)
            # if not self._check_code(code, 'set_position'):
            #     return
            code = self._arm.move_circle([250.0, 50.0, 200.0, 180.0, 0.0, 0.0], [250.0, -50.0, 200.0, 180.0, 0.0, 0.0], float(360) / 360 * 100, speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            # if not self._check_code(code, 'move_circle'):
            #     return
            # self._arm.move_gohome()
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)
    
    # Move to scan position
    def move_to_scan(self):
        global SCAN_X,SCAN_Y,SCAN_Z
        try:
            self._arm.move_gohome()
            # code = self._arm.set_tool_position(*[245.7, 27.5, 313, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            # code = self._arm.set_tool_position(*[200.0, 0.0, -313.0, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            code = self._arm.set_position(*[SCAN_X,SCAN_Y,SCAN_Z,180,0,0], speed=self._tcp_speed, mvacc=self._tcp_acc, radius=0, wait=True)
            if not self._check_code(code, 'set_position'):
                return
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)

    # Move tool position by relative x, y, z coords
    def move_by_xyz(self, x, y, z):
        try:
            code = self._arm.set_tool_position(*[x, y, z, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)

    def pickup_n_place(self, x, y, z, min_z=10, step_size=20, check_interval=0.1, offset_x=80, offset_y=0, offset_z=0):
        """Slowly moves the cobot down while suction cup on to pickup object. 
        Then places object in specified coord.
        x, y, z: The coordinate to place the object
        min_z: Minimum height to maintain, cobot can't go below this
        step_size: Step size to go down (mm)
        check_interval: Time between steps (s)
        offset_x: Offset in X-axis to compensate for camera offset (mm)
        offset_y: Offset in Y-axis to compensate for camera offset (mm)
        offset_z: Offset in Z-axis to compensate for camera offset (mm)
        """
        global SCAN_X,SCAN_Y,SCAN_Z
        init_x, init_y, init_z = self.get_cobot_position()
        print(f"Init position: {init_x}, {init_y}, {init_z}")
        try:
            # 1. Move forward to compensate for camera offset
            code = self._arm.set_tool_position(*[offset_x, offset_y, offset_z, 0.0, 0.0, 0.0], speed=self._tcp_speed, mvacc=self._tcp_acc, wait=True)
            # 2. Move down in small steps while checking suction
            z_moved = 0
            reached_obj = 0
            code = self._arm.set_suction_cup(True, wait=True, delay_sec=0)  # Turn suction ON before moving
            while z_moved < (init_z - min_z - step_size): # Don't move more than current z
                code = self._arm.set_tool_position(*[0, 0, step_size, 0.0, 0.0, 0.0], speed=25, mvacc=self._tcp_acc, wait=True)
                time.sleep(check_interval)
                code, suction_status = self._arm.get_tgpio_digital()  # Digital input from suction cup
                if code == 0 and suction_status[0] == 1:  # Detected object sucked
                    reached_obj = 1
                    self.pprint("[SUCTION] Object detected by vacuum. Stopping downward motion.")
                    break
                z_moved += step_size
            if reached_obj != 1:
                self.pprint('Failed to reach object. Returning to initial position')
                code = self._arm.set_position(x=init_x, y=init_y, z=init_z, roll=180, pitch=0, yaw=0, speed=100, wait=True)
                return
            # 3. Close gripper to grab object
            code = self._arm.set_suction_cup(True, wait=True, delay_sec=0)
            time.sleep(1)
            # 4. Go to drop location
            code = self._arm.set_position(x=x, y=y, z=80, roll=180, pitch=0, yaw=0, speed=25, wait=True) # Set z-coord to 80 first above xy drop coords
            code = self._arm.set_position(x=x, y=y, z=z, roll=180, pitch=0, yaw=0, speed=25, wait=True)
            time.sleep(0.5)
            # 5. Release object
            code = self._arm.set_suction_cup(False, wait=True, delay_sec=0)
            time.sleep(1)
            # 6. Return to initial position
            # code = self._arm.set_position(x=init_x, y=init_y, z=init_z, roll=180, pitch=0, yaw=0, speed=100, wait=True)
            # OR 6. Return to scan position
            code = self._arm.set_position(*[SCAN_X,SCAN_Y,SCAN_Z,180,0,0], speed=self._tcp_speed, mvacc=self._tcp_acc, radius=0, wait=True)
            if not self._check_code(code, 'set_position'):
                return
        except Exception as e:
            self.pprint('MainException: {}'.format(e))

    # Move to scan position
    def return_home(self):
        try:
            self._arm.move_gohome()
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)

if __name__ == '__main__':
    RobotMain.pprint('xArm-Python-SDK Version:{}'.format(version.__version__))
    arm = XArmAPI('192.168.1.224', baud_checkset=False)
    robot_main = RobotMain(arm)
    # robot_main._arm.move_gohome()
    robot_main.move_square()
    # robot_main.move_by_xyz(80, 0, 0)
    # robot_main.pickup_n_place(x=148.1, y=181.9, z=30, min_z=-11, step_size=5, check_interval=0.01, offset_x=0)
    # robot_main.run()

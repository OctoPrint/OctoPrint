# coding=utf-8
from __future__ import absolute_import
import serial
import time
from time import sleep
from threading import Thread, Event
import numpy as np

from mecode import G
from mecode.printer import Printer
import octoprint.plugin


__author__ = "Jack Minardi <jack@voxel8.co>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 Voxel8, Inc."


__plugin_name__ = "Auto Alignment"
__plugin_version__ = "0.1.0"
__plugin_description__ = "Run the auto-alignment script before each print"
__plugin_author__ = "Jack Minardi"
__plugin_description__ = "Runs the Auto Alignment code when the pseudo gcode is detected"


Ag_feature_offset = (120.000, 130.000)
matrix_feature_offset = (65.000, 130.000)
matrix_elbow_lengths = (10, 8)
Ag_elbow_lengths = (10, 8)
Ag_speed = 15*60
travel_speed = 100*60


class AlignmentAutomator(object):

    def __init__(self, g, matrix_x=[0.00000, 0.00000], matrix_y=[0.00000, 0.00000],
                 Ag_x=[0.00000, 0.00000], Ag_y=[0.00000, 0.00000],
                 nozzle_offset=[37.50000, 0.0000, -4.90000],
                 laser_offset=[18.4500, -44.52500, -19.0000, -44.52500], fudge = [0,0,0]
                ):
        self.g = g
        self.nozzle_offset = nozzle_offset
        self.laser_offset = laser_offset
        self.matrix_x = matrix_x
        self.matrix_y = matrix_y
        self.Ag_x = Ag_x
        self.Ag_y = Ag_y
        self.fudge = fudge
        self.offsetstring = None

        g.write('G1 Z10 X-2 F1000')
        g.write('G28 Y')
        g.write('G28')
        g.write('G91')

    def get_value(self):
        g = self.g
        g.write('M400')
        prof_val = int(g.write('M235', resp_needed=True)[3:-1])
        if prof_val > 10000:
            return None
        prof_val -= 5000
        return prof_val

    def detect_trace(self, direction='+x', step=0.1, tolerance=60,
                     max_travel=50, dwell=100):
        g = self.g
        sign = 1 if direction[0] == '+' else -1
        axis = direction[1]
        delta = 0
        old_value = self.get_value()
        distance_moved = 0
        while delta < tolerance:
            g.move(**{axis: sign * step})
            g.dwell(dwell)
            new_value = self.get_value()
            if new_value is None:
                break
            delta = abs(new_value - old_value)
            distance_moved = distance_moved + step
            if distance_moved > max_travel:
                break
            old_value = new_value
        g.dwell(dwell)
        position = g._current_position
        edge_position = position[axis.lower()] - (float(sign) * step / 2)
        return edge_position

    def get_1D_profile(self, direction = '+x', step = 0.03, tolerance = 0.14,
                        length = 3.4, dwell = 250, speed = 5, min_step = 0.075, start=(33.5,40,0)):
        g = self.g
        sign = 1 if direction[0] == '+' else -1
        if direction[1] == 'x':
            x_multiplier = sign
            y_multiplier = 0
        else:
            x_multiplier = 0
            y_multiplier = sign
        num_measurements = int((length/step)+1)
        array = np.zeros((num_measurements,3))
        g.abs_move(x=start[0], y=start[1])
        g.abs_move(Z=start[2])
        old_value = self.get_value()
        array[0,:] = start[0], start[1], old_value
        for i in range(num_measurements - 1):
            g.dwell(dwell)
            value = self.get_value()
            array[i,:] = start[0]+x_multiplier*i*step, start[1]+y_multiplier*i*step, value
            if min_step > step:
                g.move(**{direction[1]: 1*-sign})
                g.move(**{direction[1]: (1+step)*sign})
            g.move(**{direction[1]: step*sign})
        g.dwell(dwell)
        value = self.get_value()
        array[num_measurements-1,:]= start[0]+x_multiplier*num_measurements*step, start[1]+y_multiplier*num_measurements*step, value
        return array

    def header(self):
        g = self.g
        header = """
            M106 S0
            M125 S40
            M104 S140 ; set temperature
            G4 S35
            M280 P0 S110
            G28 ; home all axes
            G29
            M125 S39
            G90 ; use absolute coordinates
            G92 E0
            ; set temperatures
            M104 S220
            M42 P6 S0
        """
        for line in header.split('\n'):
            g.write(line)

    def footer(self):
        g = self.g
        footer = """
            M104 S0 ; turn off temperature

            G90
        """
        for line in footer.split('\n'):
            g.write(line)

    def activate_Ag(self):
        g = self.g
        g.feed(3000)
        g.move(Z=-self.nozzle_offset[2]+1.16)
        g.abs_move(X=160)
        g.abs_move(Y=0)
        g.abs_move(X=190)
        g.move(Y=20)
        g.move(X=-10)

    def deactivate_Ag(self):
        g = self.g
        g.feed(3000)
        g.abs_move(X=130)
        g.abs_move(Y=48)
        g.abs_move(X=190)
        g.abs_move(Y=21)
        g.move(X=-10)

    def pressure_on(self):
        g = self.g
        g.write('M400\n')
        g.write('M42 P2 S255\n')

    def pressure_off(self):
        g = self.g
        g.write('M400\n')
        g.write('M42 P2 S0\n')


    def print_registration_pattern(self):
        g = self.g

        self.header()

        #purge etc #should be seperate
        g.extrude = False
        g.feed(travel_speed)
        g.abs_move(Z=30)

        #print matrix feature
        g.feed(travel_speed)
        g.abs_move(55,185)
        g.abs_move(3,185)
        g.feed(170)
        g.move(E=15)
        g.dwell(2)
        g.move(E=-.2)
        g.feed(travel_speed)
        g.abs_move(3,164)
        g.abs_move(4,164)
        g.abs_move(4,185)
        g.abs_move(5,185)
        g.abs_move(5,164)
        #This essentially the same as our wiping script copied out of the config

        #g.extrude = True
        g.abs_move(x=matrix_feature_offset[0]-15,y=matrix_feature_offset[1]-(25))
        g.abs_move(Z=0.23)
        #g.extrude = False
        g.feed(travel_speed)
        g.abs_move(y=matrix_feature_offset[1])
        g.feed(960)
        g.extrude = True
        g.extrusion_multiplier = 3
        g.meander(x=6, y=matrix_elbow_lengths[1], spacing = 0.75, start = 'UL', orientation = 'y')
        g.abs_move(x=matrix_feature_offset[0])
        g.abs_move(y=matrix_feature_offset[1])
        g.move(x=-(matrix_elbow_lengths[0]+1))
        g.move(E=-4)
        g.feed(5000)
        g.move(y=-40)
        g.move(x=15)
        g.extrude=False
        g.move(Z=5)

        #print silver feature
        g.feed(travel_speed)
        self.activate_Ag()
        g.feed(travel_speed)
        g.abs_move(x=Ag_feature_offset[0]-Ag_elbow_lengths[0], y=Ag_feature_offset[1]-Ag_elbow_lengths[1])
        g.feed(Ag_speed)
        g.abs_move(Z=0.21 - self.nozzle_offset[2])
        g.feed(700)
        self.pressure_on()
        g.write('G4 S1')
        g.move(y=Ag_elbow_lengths[1])
        g.abs_move(x=Ag_feature_offset[0])
        g.abs_move(y=Ag_feature_offset[1]-Ag_elbow_lengths[1])
        self.pressure_off()
        g.move(x=-(Ag_elbow_lengths[0]/2))
        g.feed(travel_speed)
        g.move(Z=10)
        self.deactivate_Ag()

        self.footer()

    def lever_scan(self, big_step = 0.1, small_step = 0.035, start = (187, 184, 0), dwell = 0.1,  z_offset = 20):
        g = self.g
        g.feed(1000)
        g.abs_move(Z=6)
        g.feed(3000)
        g.abs_move(start[0], start[1])
        g.feed(1000)
        g.abs_move(Z=start[2])
        g.write('G92 Z{}'.format(start[2]+z_offset))

        time.sleep(.5)

        val = self.get_value()
        print "val is {}".format(val)
        time.sleep(.5)
        while val is None:
            g.move(Z=-big_step)
            g.dwell(dwell)
            val = self.get_value()
            print 'val is {}'.format(val)
        dif = 0
        tolerance = big_step*1000*1.35
        old_val = val
        while dif < tolerance:
            g.move(Z=-big_step)
            g.dwell(dwell)
            val = self.get_value()
            if val is None:
                break
            dif = abs(val - old_val)
            old_val = val
            print 'dif is {}'.format(dif)
        g.move(Z=big_step*2.5)
        old_val = self.get_value()
        dif = 0
        tolerance = small_step*1000*1.35
        while dif < tolerance:
            g.move(Z=-small_step)
            g.dwell(dwell)
            val = self.get_value()
            if val is None:
                break
            dif = abs(val - old_val)
            old_val = val
        position = g._current_position
        z_pos = position['Z']
        prof_val = old_val
        g.abs_move(Z=start[2]+z_offset)
        g.set_home(Z=start[2])
        g.abs_move(Z=8)

        return z_pos, prof_val

    def scan_all_levers(self):
        g = self.g
        fff_z, _ = self.lever_scan(start=(187, 184, 0))
        g.write('M104 S210')
        self.activate_Ag()
        ag_z, _ = self.lever_scan(start=(3, 184, 0))
        self.deactivate_Ag()
        self.nozzle_offset[2] = fff_z - ag_z + self.fudge[2]

    def locate_all_traces(self):
        g = self.g
        g.feed(4000)
        g.abs_move(Z=2)
        g.abs_move(x=matrix_feature_offset[0]-self.laser_offset[0]-1.5,
            y=matrix_feature_offset[1]-self.laser_offset[1]-4)
        time.sleep(1)
        self.matrix_x[0] = self.detect_trace(direction = '+x', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)
        g.abs_move(x=matrix_feature_offset[0]-self.laser_offset[0]+2.5,
            y=matrix_feature_offset[1]-self.laser_offset[1]-4)
        self.matrix_x[1] = self.detect_trace(direction = '-x', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)
        g.abs_move(x=matrix_feature_offset[0]-self.laser_offset[0]-4,
            y=matrix_feature_offset[1]-self.laser_offset[1]+3)
        self.matrix_y[0] = self.detect_trace(direction = '-y', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)
        g.abs_move(x=matrix_feature_offset[0]-self.laser_offset[0]-4,
            y=matrix_feature_offset[1]-self.laser_offset[1]-3)
        self.matrix_y[1] = self.detect_trace(direction = '+y', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)

        # silver part
        g.abs_move(x=Ag_feature_offset[0]-self.laser_offset[2]-2,
            y=Ag_feature_offset[1]-self.laser_offset[1]-4)
        time.sleep(1)
        self.Ag_x[0] = self.detect_trace(direction = '+x', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)

        g.abs_move(x=Ag_feature_offset[0]-self.laser_offset[2]+3,
            y=Ag_feature_offset[1]-self.laser_offset[1]-4)
        self.Ag_x[1] = self.detect_trace(direction = '-x', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)

        g.abs_move(x=Ag_feature_offset[0]-self.laser_offset[2]-3.5,
            y=Ag_feature_offset[1]-self.laser_offset[1]-2)
        self.Ag_y[0] = self.detect_trace(direction = '+y', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)

        g.abs_move(x=Ag_feature_offset[0]-self.laser_offset[2]-3.5,
            y=Ag_feature_offset[1]-self.laser_offset[1]+4)
        self.Ag_y[1] = self.detect_trace(direction = '-y', step = 0.1, tolerance = 60,
                        max_travel = 10, dwell = 0.1)

    def calculate_offsets(self):
        measured_trace_offset_x = sum(self.Ag_x)/len(self.Ag_x) - sum(self.matrix_x)/len(self.matrix_x)
        measured_trace_offset_y = sum(self.Ag_y)/len(self.Ag_y) - sum(self.matrix_y)/len(self.matrix_y)
        feature_coord_offset_x = Ag_feature_offset[0]- matrix_feature_offset[0]
        feature_coord_offset_y = Ag_feature_offset[1]- matrix_feature_offset[1]
        tool_offset_x = measured_trace_offset_x - feature_coord_offset_x
        tool_offset_y = measured_trace_offset_y - feature_coord_offset_y
        self.nozzle_offset[0] =  tool_offset_x
        self.nozzle_offset[1] = tool_offset_y
        offset_string = 'M218 T1 X{} Y{} Z{}'.format(*self.nozzle_offset)
        return offset_string

    def full_alignment(self):
        g = self.g
        g.move(X=-3)
        g.write('M106')
        g.write('M104 S145')
        self.scan_all_levers()
        g.write('M106 S0')
        g.write('M109 S220') #For reliable extrusion at 250 micron nozzle. Set to 210 for 350 micron, and 200 or lower for larger
        self.print_registration_pattern()
        self.locate_all_traces()
        g.move(Z=10)
        offsets = self.calculate_offsets()
        self.offsetstring = offsets
        g.write('M218 T0 X0 Y0 Z0')
        g.write(offsets)


class AutoAlignmentPlugin(octoprint.plugin.EventHandlerPlugin):

    def __init__(self):
        self.aligning = False
        self.event = Event()
        self.event.set()
        self._write_buffer = []
        self._fake_ok = False
        self._temp_resp_len = 0

    def on_event(self, event, payload):
        if event == 'PrintCancelled':
            self.relinquish_control()
        if event == 'PrintPaused':
            self.g._p.paused = True
        if event == 'PrintResumed':
            self.g._p.paused = False

    def print_started_sentinel(self, comm, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if 'M900' in cmd:
            self.event.clear()
            self.aligning = True
            self._align_thread = Thread(target=self.align, name='Align')
            sleep(1)
            self._align_thread.start()
            return None
        return cmd

    def align(self):
        self._logger.info('Alignment started')
        self.g = g = G(
            print_lines=False,
            aerotech_include=False,
            direct_write=True,
            direct_write_mode='serial',
            layer_height = 0.19,
            extrusion_width = 0.4,
            filament_diameter = 1.75,
            extrusion_multiplier = 1.00,
            setup=False,
        )
        g._p = Printer()
        g._p.connect(self.s)
        g._p.start()


        self.AA = AA = AlignmentAutomator(g)
        AA.full_alignment()


        #g.write('G91')
        #g.feed(500)
        #g.move(10)
        #g.move(-10)
        #g.move(10)
        #g.move(-1)
        #g.move(10)
        #g.move(-1)
        #g.move(10)
        #g.feed(6000)

        self.relinquish_control()

    def relinquish_control(self):
        self._logger.info('Resetting Line Number to 0')
        self.g._p.reset_linenumber()
        self._logger.info('Tearing down, waiting for buffer to clear.')
        self.g.teardown()
        self._logger.info('teardown called, returning control to OctoPrint')
        self.aligning = False
        self._fake_ok = True
        self.event.set()

    def readline(self, *args, **kwargs):
        out = True
        if self.aligning:
            out = self.event.wait(2)
        if out:
            if self._fake_ok:
                self._fake_ok = False
                return 'ok\n'
            resp = self.s.readline(*args, **kwargs)
        else:
            if len(self.g._p.temp_readings) > self._temp_resp_len:
                self._temp_resp_len = len(self.g._p.temp_readings)
                resp = self.g._p.temp_readings[-1]
            else:
                resp = 'echo: Alignment script is running' if self.AA.offsetstring is None else self.AA.offsetstring
        return resp

    def write(self, data):
        if not self.aligning:
            return self.s.write(data)
        else:
            self._logger.warn('Write called when Mecode has control: ' + str(data))

    def close(self):
        return self.s.close()

    def serial_factory(self, comm_instance, port, baudrate, connection_timeout):
        if port == 'VIRTUAL':
            return None
        if port is None or port == 'AUTO':
            # no known port, try auto detection
            comm_instance._changeState(comm_instance.STATE_DETECT_SERIAL)
            serial_obj = comm_instance._detectPort(False)
            if serial_obj is None:
                comm_instance._log("Failed to autodetect serial port")
                comm_instance._errorValue = 'Failed to autodetect serial port.'
                comm_instance._changeState(comm_instance.STATE_ERROR)
                return None

        # connect to regular serial port
        comm_instance._log("Connecting to: %s" % port)
        if baudrate == 0:
            serial_obj = serial.Serial(str(port), 115200, timeout=connection_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
        else:
            serial_obj = serial.Serial(str(port), baudrate, timeout=connection_timeout, writeTimeout=10000, parity=serial.PARITY_ODD)
        serial_obj.close()
        serial_obj.parity = serial.PARITY_NONE
        serial_obj.open()

        self.s = serial_obj
        return self


def __plugin_load__():
    global __plugin_hooks__
    global __plugin_implementation__

    plugin = AutoAlignmentPlugin()

    __plugin_implementation__ = plugin
    __plugin_hooks__ = {
        "octoprint.comm.transport.serial.factory": plugin.serial_factory,
        "octoprint.comm.protocol.gcode.queuing": plugin.print_started_sentinel,
    }

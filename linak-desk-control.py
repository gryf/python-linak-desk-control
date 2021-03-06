# Application to let your desk dance.
# Copyright (C) 2018 Lukas Schreiner <dev@lschreiner.de>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this
# program. If not, see <https://www.gnu.org/licenses/>.

import argparse
import ctypes
import logging
import sys
import time

import usb1

VENDOR_ID = 0x12d3  # Linak
PRODUCT_ID = 0x0002  # DeskLine CBD Control Box

REQ_INIT = 0x0303
REQ_GET_STATUS = 0x0304
REQ_MOVE = 0x0305
REQ_GET_EXT = 0x0309

TYPE_SET_CI = 0x21
TYPE_GET_CI = 0xA1

HID_REPORT_GET = 0x01
HID_REPORT_SET = 0x09

CMD_STATUS_REPORT = 4
LEN_STATUS_REPORT = 64
NRB_STATUS_REPORT = 56

CMD_MODE_OF_OPERATION = 3
CMD_GET_LIN_DATA = 4
CMD_CONTROL_CBC = 5
CMD_CONTROL_TD = 6
CMD_CONTROL_CBD_TD = 8
CMD_GET_LIN_DATA_EXT = 9

DEF_MODE_OF_OPERATION = 4

LINAK_TIMEOUT = 1000

HEIGHT_MOVE_DOWNWARDS = 32767
HEIGHT_MOVE_UPWARDS = 32768
HEIGHT_MOVE_END = 32769


class Logger:
    """
    Simple logger class with output on console only
    """
    def __init__(self, logger_name):
        """
        Initialize named logger
        """
        self._log = logging.getLogger(logger_name)
        self.setup_logger()
        self._log.set_verbose = self.set_verbose

    def __call__(self):
        """
        Calling this object will return configured logging.Logger object with
        additional set_verbose() method.
        """
        return self._log

    def set_verbose(self, verbose_level):
        """
        Change verbosity level. Default level is warning.
        """
        ver_map = {0: logging.CRITICAL,
                   1: logging.ERROR,
                   2: logging.WARNING,
                   3: logging.INFO,
                   4: logging.DEBUG}
        self._log.setLevel(ver_map.get(verbose_level, ver_map[4]))

    def setup_logger(self):
        """
        Create setup instance and make output meaningful :)
        """
        if self._log.handlers:
            # need only one handler
            return

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.set_name("console")
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(console_formatter)
        self._log.addHandler(console_handler)
        self._log.setLevel(logging.WARNING)


LOG = Logger(__name__)()


class Status(object):
    positionLost = True
    antiColision = True
    overloadDown = True
    overloadUp = True
    unknown = 4

    @classmethod
    def from_buf(cls, buf):
        self = cls()
        attr = ['positionLost', 'antiColision', 'overloadDown', 'overloadUp']
        bitlist = '{:0>8s}'.format(bin(int(buf, base=16)).lstrip('0b'))
        for index, attr_name in enumerate(attr):
            setattr(self, attr_name, bitlist[index] == '1')
        # set unknown
        self.unknown = int(buf[1:], 16)

        return self


class StatusPositionSpeed(object):
    pos = None
    status = None
    speed = 0

    @classmethod
    def from_buf(cls, buf):
        self = cls()
        self.pos = int(buf[2:4] + buf[:2], 16)
        self.status = Status.from_buf(buf[4:6])
        self.speed = int(buf[6:8], 16)

        return self


class ValidFlags(object):
    ID00_Ref1_pos_stat_speed = True
    ID01_Ref2_pos_stat_speed = True
    ID02_Ref3_pos_stat_speed = True
    ID03_Ref4_pos_stat_speed = True
    ID10_Ref1_controlInput = True
    ID11_Ref2_controlInput = True
    ID12_Ref3_controlInput = True
    ID13_Ref4_controlInput = True
    ID04_Ref5_pos_stat_speed = True
    ID28_Diagnostic = True
    ID05_Ref6_pos_stat_speed = True
    ID37_Handset1command = True
    ID38_Handset2command = True
    ID06_Ref7_pos_stat_speed = True
    ID07_Ref8_pos_stat_speed = True
    unknown = True

    @classmethod
    def from_buf(cls, buf):
        self = cls()
        attr = ['ID00_Ref1_pos_stat_speed',
                'ID01_Ref2_pos_stat_speed',
                'ID02_Ref3_pos_stat_speed',
                'ID03_Ref4_pos_stat_speed',
                'ID10_Ref1_controlInput',
                'ID11_Ref2_controlInput',
                'ID12_Ref3_controlInput',
                'ID13_Ref4_controlInput',
                'ID04_Ref5_pos_stat_speed',
                'ID28_Diagnostic',
                'ID05_Ref6_pos_stat_speed',
                'ID37_Handset1command',
                'ID38_Handset2command',
                'ID06_Ref7_pos_stat_speed',
                'ID07_Ref8_pos_stat_speed',
                'unknown']
        for idx, bit in enumerate(bin(int(buf, base=16))[2:].zfill(16)):
            setattr(self, attr[idx], bit == '1')

        return self


class StatusReport(object):
    featureRaportID = 0
    numberOfBytes = 0
    validFlag = None
    ref1 = None
    ref2 = None
    ref3 = None
    ref4 = None
    ref1cnt = 0
    ref2cnt = 0
    ref3cnt = 0
    ref4cnt = 0
    ref5 = None
    diagnostic = None
    undefined1 = None
    handset1 = 0
    handset2 = 0
    ref6 = None
    ref7 = None
    ref8 = None
    undefined2 = None

    @classmethod
    def from_buf(cls, buf):
        self = cls()
        raw = buf.hex()
        self.featureRaportID = buf[0]
        self.numberOfBytes = buf[1]
        self.validFlag = ValidFlags.from_buf(raw[4:8])
        self.ref1 = StatusPositionSpeed.from_buf(raw[8:8+8])
        self.ref2 = StatusPositionSpeed.from_buf(raw[16:16+8])
        self.ref3 = StatusPositionSpeed.from_buf(raw[24:24+8])
        self.ref4 = StatusPositionSpeed.from_buf(raw[32:32+8])
        self.ref1cnt = int(raw[42:44] + raw[40:42], 16)
        self.ref2cnt = int(raw[46:48] + raw[44:46], 16)
        self.ref3cnt = int(raw[50:52] + raw[48:50], 16)
        self.ref4cnt = int(raw[54:56] + raw[52:54], 16)
        self.ref5 = StatusPositionSpeed.from_buf(raw[56:56+8])
        self.diagnostic = raw[64:64+16]
        self.undefined1 = raw[80:84]
        self.handset1 = int(raw[86:88] + raw[84:86], 16)
        self.handset2 = int(raw[88:90] + raw[86:88], 16)
        self.ref6 = StatusPositionSpeed.from_buf(raw[90:90+8])
        self.ref7 = StatusPositionSpeed.from_buf(raw[98:98+8])
        self.ref8 = StatusPositionSpeed.from_buf(raw[106:106+8])
        self.undefined2 = raw[114:]

        return self


class LinakController(object):
    _handle = None
    _ctx = None

    def __init__(self):
        self._ctx = usb1.USBContext()
        # self._ctx.setDebug(4)
        self._handle = self._ctx.openByVendorIDAndProductID(VENDOR_ID,
                                                            PRODUCT_ID,
                                                            skip_on_error=True)
        if not self._handle:
            raise Exception('Could not connect to usb device')

        self._handle.claimInterface(0)
        self._init_device()

    def close(self):
        if self._handle:
            self._handle.releaseInterface(0)

        del self._handle
        del self._ctx

    def _control_write_read(self, request_type, request, value, index, data,
                            timeout=0):
        data, data_buffer = usb1.create_initialised_buffer(data)
        transferred = self._handle._controlTransfer(request_type, request,
                                                    value, index, data,
                                                    ctypes.sizeof(data),
                                                    timeout)
        return transferred, data_buffer[:transferred]

    def _get_status_report(self):
        buf = bytearray(b'\x00' * LEN_STATUS_REPORT)
        buf[0] = CMD_STATUS_REPORT
        # print('> {:s}'.format(buf.hex()))
        _, buf = self._control_write_read(TYPE_GET_CI,
                                          HID_REPORT_GET,
                                          REQ_GET_STATUS,
                                          0,
                                          buf,
                                          LINAK_TIMEOUT)

        # check if the response match to request!
        if buf[0] != CMD_STATUS_REPORT:
            raise Exception('Invalid status report received!')

        return buf

    def _set_status_report(self):
        buf = bytearray(b'\x00' * LEN_STATUS_REPORT)
        buf[0] = CMD_MODE_OF_OPERATION
        buf[1] = DEF_MODE_OF_OPERATION
        buf[2] = 0
        buf[3] = 251

        amount, buf = self._control_write_read(TYPE_SET_CI,
                                               HID_REPORT_SET,
                                               REQ_INIT,
                                               0,
                                               buf,
                                               LINAK_TIMEOUT)

        if amount != LEN_STATUS_REPORT:
            raise Exception('Device is not ready yet. Initialization failed '
                            'in step 1.')

    def _move(self, height):
        buf = bytearray(b'\x00' * LEN_STATUS_REPORT)
        buf[0] = CMD_CONTROL_CBC

        hHex = '{:04x}'.format(height)
        hHigh = int(hHex[2:], 16)
        hLow = int(hHex[:2], 16)

        buf[1] = hHigh
        buf[2] = hLow
        buf[3] = hHigh
        buf[4] = hLow
        buf[5] = hHigh
        buf[6] = hLow
        buf[7] = hHigh
        buf[8] = hLow

        amount, buf = self._control_write_read(TYPE_SET_CI,
                                               HID_REPORT_SET,
                                               REQ_MOVE,
                                               0,
                                               buf,
                                               LINAK_TIMEOUT)
        return amount == LEN_STATUS_REPORT

    def _move_down(self):
        return self._move(HEIGHT_MOVE_DOWNWARDS)

    def _move_up(self):
        return self._move(HEIGHT_MOVE_UPWARDS)

    def _move_end(self):
        return self._move(HEIGHT_MOVE_END)

    def _is_status_report_not_ready(self, buf):
        if buf[0] != CMD_STATUS_REPORT or buf[1] != NRB_STATUS_REPORT:
            return False

        for i in range(2, LEN_STATUS_REPORT - 5):
            if buf[i] != 0:
                return False

        return True

    def _init_device(self):
        buf = self._get_status_report()
        if not self._is_status_report_not_ready(buf):
            return
        else:
            LOG.error('Device not ready!')

        self._set_status_report()
        time.sleep(0.001)
        if not self._move_end():
            raise Exception('Device not ready - initialization failed on step '
                            '2 (move_end)')

        time.sleep(0.1)

    def move(self, target):
        retry_count = max_retry = 3
        epsilon = 13
        prev_height = 0

        while True:
            self._move(target)
            time.sleep(0.2)

            buf = self._get_status_report()
            r = StatusReport.from_buf(buf)
            distance = r.ref1cnt - r.ref1.pos
            delta = abs(prev_height - r.ref1.pos)
            if (abs(distance) <= epsilon or delta <= epsilon or
                    prev_height == r.ref1.pos):
                retry_count -= 1
            else:
                retry_count = max_retry

            LOG.info('Current height: %s; target height: %s; '
                     'distance: %s', r.ref1.pos, target, distance)

            if retry_count == 0:
                break

            prev_height = r.ref1.pos

        return abs(r.ref1.pos - target) <= epsilon

    def get_height(self):
        buf = self._get_status_report()
        r = StatusReport.from_buf(buf)

        return r.ref1.pos, r.ref1.pos/98.0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get the control on your '
                                     'desk!')
    subparsers = parser.add_subparsers(help='supported commands',
                                       dest='subcommand')
    subparsers.required = True
    parser_status = subparsers.add_parser('status', help='Get status of the '
                                          'device')
    parser_move = subparsers.add_parser('move', help='Move to the desired '
                                        'height')
    parser_move.add_argument('height', type=int)
    parser.add_argument("-v", "--verbose", help='be verbose. Adding more "v" '
                        'will increase verbosity', action="count", default=0)

    args = parser.parse_args()

    LOG.set_verbose(args.verbose)

    co = LinakController()
    try:
        if args.subcommand == 'move':
            r = co.move(args.height)
            if r:
                LOG.info('Command executed successfuly')
            else:
                LOG.error('Command failed')
        elif args.subcommand == 'status':
            h, hcm = co.get_height()
            LOG.info('Current height is: %s / %.2fcm', h, hcm)
    except Exception as e:
        co.close()
        raise e
    finally:
        co.close()

# the following is distilled (reduced) from `py-videocore`, which has a larger purpose but
# happens to include these methods. The following has a MIT license.
# source: https://github.com/nineties/py-videocore

import os
from array import array
from struct import calcsize, pack_into, unpack_from
from fcntl import ioctl

IOCTL_MAILBOX = 0xC0046400   # _IOWR(100, 0, char *)
IOCTL_BUFSIZE = 1024

PROCESS_REQUEST = 0x00000000
REQUEST_SUCCESS = 0x80000000
PARSE_ERROR     = 0x80000001

class MailBoxException(Exception):
  'mailbox exception'

class MailBox(object):
  def __init__(self):
    self.fd = os.open('/dev/vcio', os.O_RDONLY)

  def close(self):
    if self.fd:
      os.close(self.fd)
    self.fd = None

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return exc_value is None

  def _simple_call(self, name, tag, req_fmt, res_fmt, args):
    'Call a method which has constant length response.'

    print("calling: {}".format(name))
    # Since the mailbox property interface overwrites the request tag buffer for returning
    # values to the host, size of the buffer must have enough space for both request
    # arguments and returned values. It must also be 32-bit aligned.
    tag_size = (max(calcsize(req_fmt), calcsize(res_fmt)) + 3) // 4 * 4
    print("tag sz: {}".format(tag_size))

    buf = array('B', [0]*IOCTL_BUFSIZE)
    pack_into('=5L' + req_fmt + 'L', buf, 0,
            *([24 + tag_size, PROCESS_REQUEST, tag, tag_size, tag_size] + args + [0]))

    ioctl(self.fd, IOCTL_MAILBOX, buf, True)

    r = unpack_from('=5L' + res_fmt, buf, 0)
    if r[1] != REQUEST_SUCCESS:
      raise MailBoxException('Request failed', name, *args)

    assert(r[4] == 0x80000000 | calcsize(res_fmt))
    print("boom. returning.")
    return r

  @classmethod
  def _add_simple_method(cls, name, tag, req_fmt, res_fmt):
    print("adding method: {}".format(name))
    def f(self, *args):
      r = self._simple_call(name, tag, req_fmt, res_fmt, list(args))[5:]
      n = len(r)
      if n == 1:
        print(" n1")
        return r[0]
      elif n > 1:
        print(" n>1")
        return r
    setattr(cls, name, f)

MAILBOX_METHODS = [
    ('get_temperature',                  0x00030006,  'L',    'LL'),
    ('get_max_temperature',              0x0003000a,  'L',    'LL'),
    ('get_throttled',                    0x00030046,  '',     'L'),

]
for name, tag, req_fmt, res_fmt in MAILBOX_METHODS:
  MailBox._add_simple_method(name, tag, req_fmt, res_fmt)


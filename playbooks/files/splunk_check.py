#!/bin/python


import lxc
import tempfile
import re
import datetime
import argparse

# Maas-specific libraries
from maas_common import metric
from maas_common import metric_bool
from maas_common import print_output
from maas_common import status_ok
from maas_common import status
from maas_common import status_err

# Check the status of log shipping to the Splunk home base
def check_splunk_forwarder(container_name=''):

      metrics = {'splunk_active' : False, 'splunk_connected' : False, 'splunk_shipping' : False}
      cont = lxc.Container(container_name)

      if not (cont.init_pid > 1 and
              cont.running and
              cont.state == "RUNNING"):
          raise maas_common.MaaSException('Container %s not in running state' %
                                           cont.name)

      try:
         with tempfile.TemporaryFile() as tmpfile:
            # Is Splunk running?
            if cont.attach_wait(lxc.attach_run_command, ['service', 'splunk', 'status'], stderr=stdout, stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               if "splunkd is running" in output:
                  metrics['splunk_active'] = True

            # Is the Splunk forwarder connected to the home base?
            if cont.attach_wait(lxc.attach_run_command, ['netstat', '-ntap'], stderr=stdout, stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               result = re.search('ESTABLISHED ([0-9]){1,6}/splunkd', output)
               if result.group(0):
                  metrics['splunk_connected'] = True

            # Are logs actively being shipped to the log file Splunk monitors?
            if cont.attach_wait(lxc.attach_run_command, ['stat', '-c', '%y', '/var/backup/rsyslog/rsyslog-aggregate.log'], stderr=stdout, stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               modTimestamp = re.search('([0-9]{4}-[0-9]{2}-[0-9]{2}) ([0-9]{2}:[0-9]{2})', output)
               currTime = str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M'))

               if modTimestamp is not None:
                 if currTime == modTimestamp.group(0):
                   metrics['splunk_shipping'] = True
               else:
                 msg = ('The aggregate log file could not be found.')
                 raise maas_common.MaasException(msg)

      except maas_common.MaaSException as e:
        status_err(str(e), force_print=True, m_name="splunk_check")

      finally:
        return metrics

def parse_args():
    parser = argparse.ArgumentParser(
        description='Check Splunk forwarder ')
    parser.add_argument('--container', nargs='?',
                        help='Name of the rsyslog container to check against')
    return parser.parse_args()

def main():
  try:
    args = parse_args()
    metrics = check_splunk_forwarder(container_name=args.container)

    status_ok(m_name="splunk_check")

    metric_bool("splunk_active", metrics.get("splunk_active"), m_name="splunk_check")
    metric_bool("splunk_connected", metrics.get("splunk_connected"), m_name="splunk_check")
    metric_bool("splunk_shipping", metrics.get("splunk_shipping"), m_name="splunk_check")

  except maas_common.MaaSException as e:
     status_err(str(e), force_print=True, m_name="splunk_check")

if __name__ == '__main__':
    args = parse_args()
    with print_output():
        main()

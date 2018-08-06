import lxc
import tempfile
import re
import datetime
import argparse
import maas_common

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
            if cont.attach_wait(lxc.attach_run_command, ['service', 'splunk', 'status'], stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               if "splunkd is running" in output:
                  metrics['splunk_active'] = True

            # Is the Splunk forwarder connected to the home base?
            if cont.attach_wait(lxc.attach_run_command, ['netstat', '-ntap'], stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               result = re.search('ESTABLISHED ([0-9]){1,6}/splunkd', output)
               if result.group(0):
                  metrics['splunk_connected'] = True

            # Are logs actively being shipped to the log file Splunk monitors?
            if cont.attach_wait(lxc.attach_run_command, ['stat', '-c', '%y', '/var/backup/rsyslog/rsyslog-aggregate.log'], stdout=tmpfile) > -1:
               tmpfile.seek(0)
               output = tmpfile.read()

               modTimestamp = re.search('([0-9]{4}-[0-9]{2}-[0-9]{2}) ([0-9]{2}:[0-9]{2})', output)
               currTime = str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M'))

               print "modTimestamp: " + modTimestamp.group(0)
               print "currTime: " + currTime
               if not modTimestamp is None:
                 if currTime == modTimestamp.group(0):
                   metrics['splunk_shipping'] = True
               else:
                 msg = ('The aggregate log file could not be found.')
                 raise MaasException(msg)

      except maas_common.MaaSException as e:
        maas_common.status_err(str(e), force_print=True, m_name="splunk_check")

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
  except maas_common.MaaSException as e:
     maas_common.status_err(str(e), force_print=True, m_name="splunk_check")

if __name__ == '__main__':
    args = parse_args()
    with maas_common.print_output():
        main()

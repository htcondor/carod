#!/usr/bin/python
#   Copyright 2008 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

#   TEST INFORMATION:
#   This test will verify that a status update message is sent if the
#   job is runs long enough.

import qpid
import zipfile
import sys
import getopt
import os
from qpid.util import connect
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.connection import Connection
from qpid.queue import Empty
from jobhooks.functions import *

def dump_queue(queue, ses, num_msgs, to):

   # Read responses as they come in and print to the screen.
   message = 0
   count = 0
   expected = 3*int(num_msgs)

   while True:
      try:
         message = queue.get(timeout=to)
         content = message.body
         count = count + 1
         job_data = message.get('message_properties').application_headers
         print 'Headers:'
         for header in job_data.keys():
            print header + ': ' + str(job_data[header])
         print ''
         print 'Body: '
         print content
         print ''
      except Empty:
         if count < expected:
            print 'Only received %d messages but expected %d.  TEST FAILED!' % (count, expected)
         else:
            print 'Received %d messages.  TEST PASSED.' % count
         break
      except:
         print 'Unexpected exception!'
         break

      if message != 0:
        ses.message_accept(RangedSet(message.id))

   return (0)


def main(argv=None):
   #----- Initialization ----------------------------
   if argv is None:
      argv = sys.argv

   try:
      opts, args = getopt.getopt(argv[1:], 'hn:t:', ['help', 'num_messages=', 'timeout='])
   except getopt.GetoptError, error:
     print str(error)
     return(FAILURE)

   num_msgs = 1
   tout = 20
   for option, arg in opts:
      if option in ('-h', '--help'):
         print 'usage: ' + os.path.basename(argv[0]) + ' [-h|--help] [-n|--num_messages <num>] [-t|--timeout <num>]'
         return(SUCCESS)
      if option in ('-n', '--num_messages'):
         num_msgs = int(arg)
      if option in ('-t', '--timeout'):
         tout = int(arg)

   # Read the carod config file for broker info
   broker_info = read_config_file('/etc/opt/grid/carod.conf', 'Broker')

   replyTo = str(uuid4())

   # Create a client and log in to it.
   parent_socket = connect(str(broker_info['ip']), int(broker_info['port']))
   connection = Connection(sock=parent_socket)
   connection.start()

   session = connection.session(str(uuid4()))

   session.queue_declare(queue=replyTo, exclusive=True)
   session.queue_declare(queue=broker_info['queue'], exclusive=False)
   session.exchange_bind(exchange=broker_info['exchange'], queue=broker_info['queue'], binding_key='grid')
   session.exchange_bind(exchange=broker_info['exchange'], queue=replyTo, binding_key=replyTo)

   # Create the local queue. Use the queue name as destination name
   dest = replyTo 
   recv_queue = session.incoming(dest)
   print 'Messages queue: ' + dest 

   # Subscribe the local queue to the queue on the server
   session.message_subscribe(queue=replyTo, destination=dest, accept_mode=session.accept_mode.explicit)
   session.message_flow(dest, session.credit_unit.message, 0xFFFFFFFF)
   session.message_flow(dest, session.credit_unit.byte, 0xFFFFFFFF)

   work_headers = {}
   work_headers['Cmd'] = '"/bin/sleep"'
   work_headers['Arguments'] = '"10"'
   work_headers['Iwd'] = '"/tmp"'
   work_headers['Owner'] = '"rrati"'
   work_headers['JobUniverse'] = 5
   message_props = session.message_properties(application_headers=work_headers)
   message_props.reply_to = session.reply_to(broker_info['exchange'], replyTo)
   message_props.message_id = str(uuid4())

   delivery_props = session.delivery_properties(routing_key='grid')
   delivery_props.ttl = 10000

   for num in range(0, num_msgs):
      session.message_transfer(destination=broker_info['exchange'], message=Message(message_props, delivery_props, ''))
      message_props.message_id = str(uuid4())
   dump_queue(recv_queue, session, num_msgs, tout)

   # Close the session before exiting so there are no open threads.
   session.close(timeout=10)
   return(SUCCESS)

if __name__ == '__main__':
    sys.exit(main())

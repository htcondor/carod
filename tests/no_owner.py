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
#   This test will verify that it is possible to send arguments for a
#   command.  The test should receive a 2 reponses per job, and the
#   exit response for each job should have a duration of around
#   5 seconds.

import qpid
import zipfile
import sys
import getopt
import os
import re
from qpid.util import connect
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.connection import Connection
from qpid.queue import Empty
from condorutils import SUCCESS, FAILURE
from condorutils.readconfig import *
from condorutils.workfetch import *

def dump_queue(queue, ses, con, num_msgs, to, dest, broker):

   # Read responses as they come in and print to the screen.
   message = 0
   count = 0
   expected = 2*int(num_msgs)
   owner_nobody = False
   owner = ''

   while True:
      try:
         message = queue.get(timeout=to)
         content = message.body
         count = count + 1
         job_data = message.get('message_properties').application_headers
         print 'Reply Message ID: ' + str(message.get('message_properties').message_id)
         print 'Correlation ID: ' + str(message.get('message_properties').correlation_id)
         print 'Headers:'
         for header in job_data.keys():
            print header + ': ' + str(job_data[header])
            if re.match('^Owner.*', header) != None:
               if job_data[header] == '"nobody"':
                  owner_nobody = True
               owner = job_data[header]
#         print ''
#         print 'Body: '
#         print content
         print ''
      except Empty:
         if count < expected:
            print 'Only received %d messages but expected %d.  TEST FAILED!' % (count, expected)
         if owner_nobody == False:
            print 'Owner of job was "%s" NOT nobody.  TEST FAILED!' % owner
         else:
            print 'Owner of job was nobody.'
         break
      except qpid.session.Closed:
         try:
            con.close()
         except:
            pass

         # Give broker time to stablize and accept connections
         time.sleep(2)
         con = Connection(sock=connect(str(broker['ip']), int(broker['port'])))
         con.start()

         ses = con.session(str(uuid4()))

         ses.queue_declare(queue=dest, exclusive=True)
         ses.queue_declare(queue=broker['queue'], exclusive=False, durable=True)
         ses.exchange_bind(exchange='amq.direct', queue=broker['queue'], binding_key='grid')
         ses.exchange_bind(exchange='amq.direct', queue=dest, binding_key=dest)

         # Create the local queue. Use the queue name as destination name
         queue = ses.incoming(dest)

         # Subscribe the local queue to the queue on the server
         ses.message_subscribe(queue=dest, destination=dest, accept_mode=ses.accept_mode.explicit)
         ses.message_flow(dest, ses.credit_unit.message, 0xFFFFFFFFL)
         ses.message_flow(dest, ses.credit_unit.byte, 0xFFFFFFFFL)
      except:
         print 'Unexpected exception!'
         break

      if message != 0:
        ses.message_accept(RangedSet(message.id))

   return (0)


def main(argv=None):
   #----- Initialization ----------------------------
   conf_file = '/etc/condor/carod.conf'

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

   # Retrieve the carod config for broker info
   try:
      broker_info = read_condor_config('CAROD', ['BROKER_IP', 'BROKER_PORT', 'BROKER_QUEUE'])
      broker_info['ip'] = broker_info['broker_ip']
      broker_info['port'] = broker_info['broker_port']
      broker_info['queue'] = broker_info['broker_queue']
   except ConfigError, error:
      print '%s' % error.msg
      print 'Attempting to retrieve config from %s' % conf_file
      try:
         broker_info = read_config_file(conf_file, 'Broker')
      except ConfigError, error:
         print '%s' % error.msg
         print 'Exiting'
         return(FAILURE)

   replyTo = str(uuid4())

   # Create a client and log in to it.
   connection = Connection(sock=connect(str(broker_info['ip']), int(broker_info['port'])))
   connection.start()

   session = connection.session(str(uuid4()))

   session.queue_declare(queue=replyTo, exclusive=True, auto_delete=True)
   session.queue_declare(queue=broker_info['queue'], exclusive=False, durable="true")
   session.exchange_bind(exchange='amq.direct', queue=broker_info['queue'], binding_key='grid')
   session.exchange_bind(exchange='amq.direct', queue=replyTo, binding_key=replyTo)

   # Create the local queue. Use the queue name as destination name
   dest = replyTo 
   recv_queue = session.incoming(dest)
   print 'Messages queue: ' + dest 

   # Subscribe the local recv_queue to the queue on the server
   session.message_subscribe(queue=replyTo, destination=dest, accept_mode=session.accept_mode.explicit)
   session.message_flow(dest, session.credit_unit.message, 0xFFFFFFFFL)
   session.message_flow(dest, session.credit_unit.byte, 0xFFFFFFFFL)

   work_headers = {}
   work_headers['Cmd'] = '"/bin/true"'
   work_headers['Iwd'] = '"/tmp"'
   work_headers['JobUniverse'] = 5
   message_props = session.message_properties(application_headers=work_headers)
   message_props.reply_to = session.reply_to('amq.direct', replyTo)
   message_props.message_id = uuid4()
   print 'Job Request Message ID: %s' % str(message_props.message_id)

   delivery_props = session.delivery_properties(routing_key='grid', delivery_mode=2)
   delivery_props.ttl = 10000

   for num in range(0, num_msgs):
      session.message_transfer(destination='amq.direct', message=Message(message_props, delivery_props, ''))
      message_props.message_id = uuid4()
   dump_queue(recv_queue, session, connection, num_msgs, tout, dest, broker_info)

   # Close the session before exiting so there are no open threads.
   try:
      connection.close()
   except:
      pass
   try:
      session.close(timeout=10)
   except:
      pass

   return(SUCCESS)

if __name__ == '__main__':
    sys.exit(main())

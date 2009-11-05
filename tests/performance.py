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
#   This test is designed to pump as many jobs into the AMQP queues as
#   fast as possible and wait for the responses, with the intention of
#   measuring the fastest speed jobs can be gotten through the system.
#   The jobs are fast running to remove as much execute time from the
#   equation as possible.
#
#   The test takes a single argument that determines the number of
#   messages to put into the system.  The number of messages received
#   will ultimately depend on how condor is configured, but should be
#   a multiple of the number of message put into the system
#   (ie 1x, 2x, etc).  To get an accurate portrayal of a system that
#   won't lose messages, the work_fetch, reply_fetch, and job_exit
#   hooks should be configured which would result in 2x as many 
#   messages received as put into the system.

import qpid
import time
import zipfile
import sys
import getopt
import threading
from qpid.util import connect
from qpid.datatypes import Message, RangedSet, uuid4
from qpid.connection import Connection
from qpid.queue import Empty
from jobhooks.functions import *

def dump_queue(binfo, queue_name, to):
   # Create a client and log in to it.
   child_connection = Connection(sock=connect(str(binfo['ip']), int(binfo['port'])))
   child_connection.start()
   child_session = child_connection.session(str(uuid4()))
   child_session.queue_declare(queue=queue_name, exclusive=True)
   child_session.exchange_bind(exchange='amq.direct', queue=queue_name, binding_key=queue_name)

   print 'Messages queue: ' + queue_name 

   # Create the local queue. Use the queue name as destination name
   dest = queue_name 
   queue = child_session.incoming(dest)

   # Subscribe the local queue to the queue on the server
   child_session.message_subscribe(queue=queue_name, destination=dest, accept_mode=child_session.accept_mode.explicit)
   child_session.message_flow(dest, child_session.credit_unit.message, 0xFFFFFFFF)
   child_session.message_flow(dest, child_session.credit_unit.byte, 0xFFFFFFFF)

   # Read responses as they come in and print to the screen.
   message = 0
   count = 0

   while True:
      try:
         message = queue.get(timeout=to)
         count = count + 1
         if count == 1:
            print 'Received first reponse: %s ' % str(time.time())
      except Empty:
         print 'Received %s messages: %s' % (str(count), str(time.time() - to))
         break
#      except qpid.session.Closed:
#         print "Re-establishing"
#         try:
#            child_connection.close()
#         except:
#            pass
#
#         # Give broker time to stablize and accept connections
#         time.sleep(2)
#         child_connection = Connection(sock=connect(str(binfo['ip']), int(binfo['port'])))
#         child_connection.start()
#         child_session = child_connection.session(str(uuid4()))
#         child_session.queue_declare(queue=queue_name, exclusive=True)
#         child_session.exchange_bind(exchange='amq.direct', queue=queue_name, binding_key=queue_name)
#
#         # Create the local queue. Use the queue name as destination name
#         queue = child_session.incoming(dest)
#
#         # Subscribe the local queue to the queue on the server
#         child_session.message_subscribe(queue=queue_name, destination=dest, accept_mode=child_session.accept_mode.explicit)
#         child_session.message_flow(dest, child_session.credit_unit.message, 0xFFFFFFFF)
#         child_session.message_flow(dest, child_session.credit_unit.byte, 0xFFFFFFFF)
      except:
         print 'Unexpected exception!'
         break

      if message != 0:
        child_session.message_accept(RangedSet(message.id))

   child_session.close(timeout=10)
   child_connection.close()
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
      broker_info = read_condor_config('LL_BROKER', ['IP', 'PORT', 'QUEUE'])
   except config_err, error:
      print '%s' % error.msg
      print 'Attempting to retrieve config from %s' % conf_file
      try:
         broker_info = read_config_file(conf_file, 'Broker')
      except config_err, error:
         print '%s' % error.msg
         print 'Exiting'
         return(FAILURE)

   replyTo = str(uuid4())
   receive_thread = threading.Thread(target=dump_queue, args=(broker_info, replyTo, tout))
   receive_thread.start()

   # Create a client and log in to it.
   connection = Connection(sock=connect(str(broker_info['ip']), int(broker_info['port'])))
   connection.start()

   session = connection.session(str(uuid4()))

   session.queue_declare(queue=broker_info['queue'], exclusive=False, auto_delete=True)
   session.exchange_bind(exchange='amq.direct', queue=broker_info['queue'], binding_key='grid')

   work_headers = {}
   work_headers['Cmd'] = '"/bin/true"'
   work_headers['Iwd'] = '"/tmp"'
   work_headers['Owner'] = '"someone"'
   message_props = session.message_properties(application_headers=work_headers)
   message_props.reply_to = session.reply_to('amq.direct', replyTo)
   message_props.message_id = uuid4()

   delivery_props = session.delivery_properties(routing_key='grid')
   delivery_props.ttl = 10000

   count = 0
   time.sleep(2)
   print 'Started sending messages: ' + str(time.time())
   for num in range(0, num_msgs):
      session.message_transfer(destination='amq.direct', message=Message(message_props, delivery_props, ''))
      message_props.message_id = uuid4()
      count = num
   print 'Finished sending %s messages: %s' % (str(count + 1), str(time.time()))

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

'''
Monitors the Bitcoin cash blockchain (using memo.cash) for activity assocaited with the memo protocol
as described here https://memo.cash/protocol

This does not require running a local note as it interfaes with the blockchain.info server for
transactions.

Copyright 2021 Jeffrey Creem
Distributed under the MIT license - See LICENSE for details

'''

from websocket import create_connection
import requests
import json 
import time
import sys
import re

import json
from datetime import datetime
from bs4 import BeautifulSoup

from signal import signal, SIGINT
from sys import exit
import traceback
import argparse



def handler(signal_received, frame):
    global monitor
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    if 'monitor' in globals():

        monitor.flush_json_debug_capture()
    exit(0)



_urlfinderregex = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')

def linkify(text, maxlinklength=255):
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = str(url)
        if text.startswith('http://'):
            text = text.replace('http://', '', 1)
        elif text.startswith('https://'):
            text = text.replace('https://', '', 1)

        if text.startswith('www.'):
            text = text.replace('www.', '', 1)

        if len(text) > maxlinklength:
            halflength = maxlinklength / 2
            text = text[0:halflength] + '...' + text[len(text) - halflength:]

        return '<a class="comurl" href="' + url + '" target="_blank" rel="nofollow">' + text + '</a>'

    if text != None and text != '':
        return _urlfinderregex.sub(replacewithlink, text)
    else:
        return ''


class MemoUser(object):
    def __init__(self, address):
        self.address = address
        self.memo_profile_url = "https://memo.cash/profile/%s" %address

        print(self.memo_profile_url)
        profile_data = requests.get(self.memo_profile_url, verify=True)

        soup = BeautifulSoup(profile_data.text, "lxml")

        title = soup.find("meta",  {"name":"og:title"})["content"]
        self.username = title[6:-8]
        self.profile_pic_url = soup.find("meta",  {"name":"og:image"})["content"]



    def get_username(self):
        return self.username


    def get_profile_pic_url(self):
        return self.profile_pic_url


Memousers = {}


class MemoMonitor(object):

    def __init__(self, address, debug_json_data_filename,\
                 html_filename, html_history_len, replay, \
                 memo_history):
        '''
        Initializes a memo monitor. This is capable of monitoring memo's posted to the
        BCH blockchain. If address is not then only messages that originate from address
        will be written to the html_filename, otherwise all memos will be written there.

        debug_json_data_filename if not None is used either for logging all memo transactions
        or playing back from all memo transactions from a file to allow testing the logic
        of this class.

        html_filename is an output file that will be updated with the last html_history_len
        memos - either filtered to just address or to all memos.

        replay if true indicates that we should configure to read from debug_json_data_filename
        instead of writing to it.

        memo_history is a file that will contain the list of the last N memos logged to
        the html file. It is read at startup and updated during operation to allow for
        persistance of the last N messages on application restart.

        '''

        self.prefix_to_action = {
            '6d02': 'Post',
            '6d03': 'Reply', 
            '6d04': 'Like/Tip',
            '6d06': 'Follow', 
            '6d07': 'Unfollow', 
            '6d0c': 'Topic Message'}
        self.action_to_prefix = {action:prefix for (prefix, action) in self.prefix_to_action.items()}
        self.OP_RETURN = '6a'
        self.PREFIX_LEN = '02'
        self.addr = address
        self.debug_json_data_filename = debug_json_data_filename
        self.filtered_memo_list = []
        self.debug_memo_capture = []
        self.html_filename = html_filename
        self.html_history_len = 5
        self.memo_history = memo_history

        #try:
        if memo_history is not None:
                with open(self.memo_history) as f:
                    self.filtered_memo_list = json.load(f)

        self.create_html_from_memo_list()

        #except:
        #    print("No memo history found")

        if replay:
            with open(self.debug_json_data_filename) as f:
                self.debug_memo_capture = json.load(f)


    def flush_json_debug_capture(self):

        if self.debug_json_data_filename is not None and not self.Replay:
            with open(self.debug_json_data_filename, 'w') as fp:
                json.dump(self.debug_memo_capture, fp)

    def create_html_from_memo_list(self):
        with open(self.html_filename,"w") as file:
            file.write("<html><body>\n")
            file.write('<div class="divMemoTable">')
            file.write('<div class="divMemoTableBody">')
            
            for a_memo in reversed(self.filtered_memo_list):

                if a_memo['addr'] not in Memousers:
                    new_user = MemoUser(a_memo['addr'])
                    Memousers[a_memo['addr']] = new_user

                file.write('<div class="divMemoTableRow">')

                file.write('<div class="divMemoTableCell">')
                file.write("<img src=" + Memousers[a_memo['addr']].get_profile_pic_url() + ' width=32 align="left">')
                file.write("</div>") # end divMemoTableCell

                file.write('<div class="divMemoTableCell">')
                file.write(Memousers[a_memo['addr']].get_username())
                file.write(" ")

                the_time = datetime.utcfromtimestamp(a_memo['time']).strftime('%Y-%m-%d %H:%M:%S')
                file.write(the_time)
                file.write("<br>")
                file.write(linkify(a_memo['memo']))
                file.write("<br>\n")
                file.write("</div>") # end divMemoTableCell                    
                file.write("</div>") # end divMemoTableRow

            file.write("</div>") # end divMemoableBody
            file.write("</div>") # end divMemoTable
            file.write("</html></body>\n")


    def filtered_add_to_html(self, time, memo, addr):
        ''' This class maintains an html file of the last N memos. This funciton adds the given
            memo text and time stamp (eliminating the N+1 memo of appropriate) '''

        if (self.html_filename is None) or (self.addr is not None and addr != self.addr):
            return

        try:
            self.filtered_memo_list.append({'time' : time,
                                            'memo' : memo,
                                            'addr' : addr})

            self.filtered_memo_list = self.filtered_memo_list[-1 * (self.html_history_len):]

            self.create_html_from_memo_list()

        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("*** print_tb:")
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)

        with open(self.memo_history,"w") as f:
            json.dump(self.filtered_memo_list, f)

    
    def Process_Memo_Output(self, tx, output):
        ''' Given a tx transaction that is a memo protocol transaction, and the output that contains the
            memo, decode it and process. '''

        the_time_seconds=int(tx['x']['time'])
        the_time = datetime.utcfromtimestamp(the_time_seconds).strftime('%Y-%m-%d %H:%M:%S')

        addr = tx["x"]["inputs"][0]["prev_out"]["addr"]


        if output["script"][4:8] == self.action_to_prefix['Post']:
            print("Found post from: " + addr)
            post_payload=output["script"][10:] 
            print("and the data was: " + post_payload)
            try:
                post_payload_text = bytes.fromhex(post_payload).decode('UTF-8','ignore')
                print("which seems to be: " +  post_payload_text)
                self.filtered_add_to_html(the_time_seconds, post_payload_text, addr)
            except:
                print("got error on decode")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("*** print_tb:")
                traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                traceback.print_exc()

        elif output["script"][4:8] == self.action_to_prefix['Reply']:
            print("Found reply from: " + addr)
            reply_to_txhash=output["script"][8:72] 
            reply_payload=output["script"][76:] 
            print("and the data was: " + reply_payload)
            try:
                reply_payload_text = bytes.fromhex(reply_payload).decode('UTF-8','ignore')
                print("which seems to be: " +  reply_payload_text)
                self.filtered_add_to_html(the_time_seconds, reply_payload_text, addr)
            except:
              print("got error")
              traceback.print_exc()
        else:
            print("Not a post")


    def process_tx(self, tx, log_to_debug = False):
        ''' processes the given transaction. If it is a memo transaction optionally log_to_debug file
            that we were initialized with. '''
        #
        # Grab the outputs for it
        #
        outputs = tx["x"]['out']
        
        # 
        # Each time through this loop, we check one of the outputs
        # of the transation to see if it is an OP_RETURN transaction
        # using the Memo protocol
        #
        for output in outputs:
            if (output["script"][0:2] == self.OP_RETURN) and (output["script"][2:4] == self.PREFIX_LEN) and\
                (output["script"][4:8] in self.prefix_to_action):
                #print("Found memo transaction " + tx["x"]["inputs"][0]["prev_out"]["addr"])

                if log_to_debug:
                    self.debug_memo_capture.append(tx)

                self.Process_Memo_Output(tx, output)



    def Replay(self):
        ''' Replay all of the saved transations in the debug file that we were initialized with '''

        for tx in self.debug_memo_capture:
            self.process_tx(tx, log_to_debug = False)


    def Listen(self):

        ws = create_connection("wss://ws.blockchain.info/bch/inv")
        ws.send("""{"op":"unconfirmed_sub"}""")

        while True:
            #
            # Grab transactions and process them until we are killed
            #
            tx = json.loads(ws.recv())
            self.process_tx(tx, log_to_debug = (self.debug_memo_capture != None))



     
if __name__ == '__main__':
    print ("Memo.cash Monitor")
    signal(SIGINT, handler)

    parser = argparse.ArgumentParser()

    parser.add_argument("--replay", action="store_true", help="replay from stored recording file in data_store then exit. Otherwise read from memo.cash forever.")
    parser.add_argument("--address", type=str, help="address (Legecy format) to look for")
    parser.add_argument("--html_summary", type=str, help="Write the last N memos that match the given address to the given filename")
    parser.add_argument("--memo_history", type=str, help="File that is read at start and written with a truncated history of messages")
    parser.add_argument("--debug_json_data_store", type=str, help="Optional json file to store to or read from if --replay is selected")
    args = parser.parse_args()



    monitor = MemoMonitor(args.address, args.debug_json_data_store, \
                          args.html_summary, 5, args.replay == True, args.memo_history)

    if args.replay:
        monitor.Replay()
    else:
        monitor.Listen()

    print("Done")

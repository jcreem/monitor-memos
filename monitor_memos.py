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
import shelve
from datetime import datetime

from signal import signal, SIGINT
from sys import exit
import traceback
import argparse



def handler(signal_received, frame):
    global monitor
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    del monitor
    exit(0)



class MemoMonitor(object):

    def __init__(self, address, shelf, html_filename):
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
        self.shelf = shelf
        self.filtered_memo_list = []
        self.html_filename = html_filename

    def __del__(self):

        if self.shelf != None:
            self.shelf.close()

    def filtered_add_to_html(self, time, memo):
        ''' This class maintains an html file of the last N memos. This funciton adds the given
            memo text and time stamp (eliminating the N+1 memo of appropriate) '''

        try:
            self.filtered_memo_list.append({'time'  : time,
                                            'memo' : memo })

            self.filtered_memo_list = self.filtered_memo_list[-5:]

            with open(self.html_filename,"w") as file:
                file.write("<html><body>\n")
                for a_memo in reversed(self.filtered_memo_list):
                    the_time = datetime.utcfromtimestamp(a_memo['time']).strftime('%Y-%m-%d %H:%M:%S')
                    file.write(the_time)
                    file.write(": ")
                    file.write(a_memo['memo'])
                    file.write("<br>\n")

                file.write("</html></body>\n")
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print("*** print_tb:")
            traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)

    
    def Process_Memo_Output(self, tx, output):
        ''' Given a tx transaction that is a memo protocol transaction, and the output that contains the
            memo, decode it and process. '''

        the_time_seconds=int(tx['x']['time'])
        the_time = datetime.utcfromtimestamp(the_time_seconds).strftime('%Y-%m-%d %H:%M:%S')

        #print(the_time)
        if output["script"][4:8] == self.action_to_prefix['Post']:
            print("Found post from: " + tx["x"]["inputs"][0]["prev_out"]["addr"])
            post_payload=output["script"][10:] 
            print("and the data was: " + post_payload)
            try:
                post_payload_text = bytes.fromhex(post_payload).decode('UTF-8','ignore')
                print("which seems to be: " +  post_payload_text)
                self.filtered_add_to_html(the_time_seconds, post_payload_text)
            except:
                print("got error on decode")

        elif output["script"][4:8] == self.action_to_prefix['Reply']:
            print("Found reply from: " + tx["x"]["inputs"][0]["prev_out"]["addr"])
            reply_to_txhash=output["script"][8:72] 
            reply_payload=output["script"][76:] 
            print("and the data was: " + reply_payload)
            try:
                reply_payload_text = bytes.fromhex(reply_payload).decode('UTF-8','ignore')
                print("which seems to be: " +  reply_payload_text)
                self.filtered_add_to_html(the_time_seconds, reply_payload_text)
            except:
              print("got error")

        else:
            print("Not a post")


    def process_tx(self, tx, log_to_shelf = False):
        ''' processes the given transaction. If it is a memo transaction optionally log_to_shelf file
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

                if log_to_shelf:
                    self.shelf[tx["x"]['hash']] = tx
                self.Process_Memo_Output(tx, output)



    def Replay(self):
        ''' Replay all of the saved transations in the shelf file that we were initialized with '''
        all_tx_ids = list(self.shelf.keys()) 

        for tx_id in all_tx_ids:
            tx = shelf[tx_id]
            self.process_tx(tx, log_to_shelf = False)


    def Listen(self):

        ws = create_connection("wss://ws.blockchain.info/bch/inv")
        ws.send("""{"op":"unconfirmed_sub"}""")

        while True:
            #
            # Grab transactions and process them until we are killed
            #
            tx = json.loads(ws.recv())
            self.process_tx(tx, log_to_shelf = (self.shelf != None))


     
if __name__ == '__main__':
    print ("Memo.cash Notifiier")
    signal(SIGINT, handler)

    parser = argparse.ArgumentParser()
    parser.add_argument("--data_store", type=str,help="If provided, filename used to store or replay transactions that contain memo protocol items")
    parser.add_argument("--replay", action="store_true", help="replay from stored recording file in data_store then exit. Otherwise read from memo.cash forever.")
    parser.add_argument("--address", type=str, help="address (Legecy format) to look for")
    parser.add_argument("--html_summary", type=str, help="Write the last N memos that match the given address to the given filename")

    args = parser.parse_args()


    if args.data_store is not None:
        shelf = shelve.open(args.data_store)
    else:
        shelf = None


    monitor = MemoMonitor(args.address, shelf, args.html_summary)

    if args.replay:
        monitor.Replay()
    else:
        monitor.Listen()



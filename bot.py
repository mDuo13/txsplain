#!/bin/env python

import time, re, os
from slackclient import SlackClient
import txsplain

token = os.getenv("TXSPLAIN_SLACK_TOKEN")

sc = SlackClient(token)
if not sc.rtm_connect():
    exit("Failed to connect.")

def activates_bot(msg):
    tx_hash_regex = re.compile(r"(\<@U03TC7URZ\>:?\s+)?([0-9a-f]{64})(\s+verbose)?", re.IGNORECASE)
    m = tx_hash_regex.match(msg)
    print("msg:",msg,m)
    if m:
        return m.group(2), m.group(3)
    else:
        return False, False

def tx_lookup(tx_hash, verbose):
    try:
        tx_json = txsplain.fetch(tx_hash)["result"]
        s = "https://api.ripple.com/v1/transactions/"+tx_hash+"\n"
        s += txsplain.splain(tx_json, verbose)
    except KeyError:
        s = "Couldn't find transaction %s." % tx_hash
        
    return s

while True:
    new_evts = sc.rtm_read()
    for evt in new_evts:
        print(evt)
        if "type" not in evt:
            continue
        if evt["type"] == "message" and "text" in evt:
            tx_hash,verbose = activates_bot(evt["text"])
            if tx_hash:
                chan = sc.server.channels.find(evt["channel"])
                if chan:
                    chan.send_message(tx_lookup(tx_hash, verbose))
                #print(tx_lookup(tx_hash))
    time.sleep(1)

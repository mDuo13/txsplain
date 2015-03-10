#!/bin/env python

from __future__ import print_function
import json, sys, pickle, struct

RIPPLED_HOST = "s1.ripple.com"
RIPPLED_PORT = 51234
RIPPLE_ID_HOST = "id.ripple.com"
RIPPLE_ID_PORT = 443
PICKLE_FILE = "ripnames.pkl"

FLAGS = {
    "*": {
        0x80000000: "tfFullyCanonicalSig"
    },
    "Payment": {
        0x00010000: "tfNoDirectRipple",
        0x00020000: "tfPartialPayment",
        0x00040000: "tfLimitQuality"
    },
    "AccountSet": {
        0x00010000: "tfRequireDestTag",
        0x00020000: "tfOptionalDestTag",
        0x00040000: "tfRequireAuth",
        0x00080000: "tfOptionalAuth",
        0x00100000: "tfDisallowXRP",
        0x00200000: "tfAllowXRP"
    },
    "SetRegularKey": {},
    "OfferCreate": {
        0x00010000: "tfPassive",
        0x00020000: "tfImmediateOrCancel",
        0x00040000: "tfFillOrKill",
        0x00080000: "tfSell"
    },
    "OfferCancel": {},
    "TrustSet": {
        0x00010000: "tfSetAuth",
        0x00020000: "tfSetNoRipple",
        0x00040000: "tfClearNoRipple",
        0x00100000: "tfSetFreeze",
        0x00200000: "tfClearFreeze"
    },
    "SetFee": {}
}

PATHSTEP_RIPPLING = 0x01
PATHSTEP_REDEEMING = 0x02
PATHSTEP_ORDERBOOK = 0x10
PATHSTEP_ISSUER = 0x20


if sys.version_info[:2] <= (2,7):
    import httplib
else:
    import http.client as httplib


def decode_hex(s):
    if sys.version_info.major < 3:
        return s.decode("hex")
    else:
        return bytes.fromhex(s).decode("utf-8")

    
def is_string(s):
    if sys.version_info.major < 3:
        # unicode is only defined in python 2.x
        if type(s) == str or type(s) == unicode:
            return True
    elif type(s) == str:
        return True
    else:
        return False
        
    
def dumpjson(j):
    return json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))


def splain(tx_json, verbose=True):
    global tx_parties
    tx_parties = {} # reset this once per splain
    
    msg = ""
    
    print(dumpjson(tx_json))
    msg += "\n\n"
    
    try:
        ledger = lookup_ledger(ledger_index=tx_json["ledger_index"])
    except KeyError:
        ledger = None
    tx_type = tx_json["TransactionType"]
    
    #lookup flags now so we can phrase things accordingly
    enabled_flags = []
    if "Flags" in tx_json:
        for flag_bit,flag_name in FLAGS["*"].items():
            if tx_json["Flags"] & flag_bit:
                enabled_flags.append(flag_name)
        for flag_bit,flag_name in FLAGS[tx_type].items():
            if tx_json["Flags"] & flag_bit:
                enabled_flags.append(flag_name)
    
    if tx_type == "Payment":
        msg += "This is a Payment from %s to %s.\n" % (lookup_acct(tx_json["Account"]),
                lookup_acct(tx_json["Destination"]))
    elif tx_type == "OfferCreate":
        if "tfSell" in enabled_flags:
            msg += "This is an OfferCreate, where %s offered to pay %s in order to receive at least %s.\n" % (
                    lookup_acct(tx_json["Account"]), amount_to_string(tx_json["TakerGets"]),
                    amount_to_string(tx_json["TakerPays"]) )
        else:
            msg += "This is an OfferCreate, where %s offered to pay up to %s in order to receive %s.\n" % (
                    lookup_acct(tx_json["Account"]), amount_to_string(tx_json["TakerGets"]),
                    amount_to_string(tx_json["TakerPays"]) )
        if "OfferSequence" in tx_json:
            msg += "Additionally, it was intended to cancel a previous offer with sequence #%d.\n" % tx_json["OfferSequence"]
    elif tx_type == "SetFee":
        msg += "This is a SetFee pseudo-transaction.\n"
    else:
        msg += "This is a %s transaction.\n" % tx_type
        msg += "The transaction was sent by %s.\n" % lookup_acct(tx_json["Account"])
    
    tx_meta = tx_json["meta"]#"tx-command" format
    
    if enabled_flags:
        msg += "The transaction specified the following flags: %s.\n" % ", ".join(enabled_flags)
    else:
        msg += "The transaction used no flags.\n"
    
    msg += "Sending this transaction consumed %f XRP.\n" % drops_to_xrp(tx_json["Fee"])
    
    if tx_meta["TransactionResult"] == "tesSUCCESS":
        msg += "The transaction was successful.\n"
    else:
        msg += "The transaction failed with the code %s.\n" % tx_meta["TransactionResult"]
    
    if "validated" in tx_json:
        validated = tx_json["validated"]
    else:
        validated = False
    if validated and ledger:
        msg += "This result has been validated by consensus, in ledger %d, at %s.\n" % (
                tx_json["ledger_index"], ledger["close_time_human"])
    elif validated:
        msg += "This result has been validated by consensus, in ledger %d.\n" % (tx_json["ledger_index"])
    else:
        msg += "This result is provisionally part of ledger %d.\n" % tx_json["ledger_index"]
        
    if tx_type == "Payment":
        if "SendMax" in tx_json:
            msg += "It was instructed to deliver %s by spending up to %s.\n" % (
                    amount_to_string(tx_json["Amount"],any_if=tx_json["Destination"]), 
                    amount_to_string(tx_json["SendMax"],any_if=tx_json["Account"]))
        else:
            msg += "It was instructed to deliver %s.\n" % amount_to_string(tx_json["Amount"], any_if=tx_json["Destination"])
        if "delivered_amount" in tx_meta and tx_meta["delivered_amount"] != "unavailable":
            msg += "It actually delivered %s.\n" % amount_to_string(tx_meta["delivered_amount"])
    
    if "Memos" in tx_json:
        for wrapper in tx_json["Memos"]:
            memo = wrapper["Memo"]
            if "MemoType" in memo and "MemoFormat" in memo:
                memotype = decode_hex(memo["MemoType"])
                memoformat = decode_hex(memo["MemoFormat"])
                if memotype == "client":
                    msg += "A memo indicates it was sent with the client '%s'.\n" % memoformat
    
    if verbose and "Paths" in tx_json:
        msg += describe_paths(tx_json["Paths"])
    
    if verbose and "AffectedNodes" in tx_meta:
        msg += "It affected %d nodes in the global ledger, including:\n" % len(
                tx_meta["AffectedNodes"])
        for wrapper in tx_meta["AffectedNodes"]:
            if "DeletedNode" in wrapper:
                node = wrapper["DeletedNode"]
                msg += "..  It deleted %s.\n" % describe_node(node)
            elif "CreatedNode" in wrapper:
                node = wrapper["CreatedNode"]
                msg += "..  It created %s.\n" % describe_node(node)
            if "ModifiedNode" in wrapper:
                node = wrapper["ModifiedNode"]
                msg += "..  It modified %s%s.\n" % (describe_node(node), 
                        describe_node_changes(node))
                        
    if "TransactionIndex" in tx_meta:
        if ledger:
            msg += "It was transaction #%d of %d total transactions in ledger %s.\n" % (
                tx_meta["TransactionIndex"]+1, len(ledger["transactions"]) ,
                #                          ^-- convert 0-based to 1-based
                ledger["ledger_index"])
        else:
            msg += "It was transaction #%d in ledger %s.\n" % ( tx_meta["TransactionIndex"]+1, tx_json["ledger_index"] )
    
    msg = parties() + msg
    
    return msg


def parties():
    global tx_parties
    
    s = "Parties: \n"
    for addr,alias in tx_parties.items():
        s += ".. %s: %s\n" % (addr, alias)
        
    return s

def describe_paths(pathset):
    msg = "It specified %d paths other than the default one:\n" % len(pathset)
    for path in pathset:
        ptext = "Source - "
        for step in path:
            if step["type"] & PATHSTEP_ORDERBOOK:
                if step["type"] & PATHSTEP_ISSUER:
                    currency = "%s.%s" % (step["currency"], 
                            lookup_acct(step["issuer"], tilde=False))
                else:
                    currency = step["currency"]
                ptext += "Orderbook:%s - " % step["currency"]
            if step["type"] & PATHSTEP_RIPPLING:
                ptext += "%s - " % lookup_acct(step["account"])
        ptext += "Destination"
        msg += "..  %s\n" % ptext
        
    return msg

    
def describe_node(node):
    nodetype = node["LedgerEntryType"]
    # DeletedNode/ModifiedNode have FinalFields; CreateNode has NewFields
    if "FinalFields" in node:
        node_fields = node["FinalFields"]
    elif "NewFields" in node:
        node_fields = node["NewFields"]
    elif "PreviousFields" in node:
        node_fields = node["PreviousFields"]
    else:
        raise KeyError("affected node had no fields")
    
    if nodetype == "Offer":
        if "TakerPays" in node_fields and "TakerGets" in node_fields:
            taker_pays = node_fields["TakerPays"]
            taker_gets = node_fields["TakerGets"]            
            return "%s's Offer to buy %s for %s" % (
                    lookup_acct(node_fields["Account"]), 
                    amount_to_string(taker_pays), amount_to_string(taker_gets))
        else:
            #probably shouldn't get here, but handle it gracefully
            return "%s's Offer" % lookup_acct(node_fields["Account"])
            
    if nodetype == "RippleState":
        return "the trust line between %s and %s" % (
                lookup_acct(node_fields["HighLimit"]["issuer"]), 
                lookup_acct(node_fields["LowLimit"]["issuer"]))
            
    if nodetype == "DirectoryNode":
        if "Owner" in node_fields:
            return "a Directory owned by %s" % lookup_acct(node_fields["Owner"])
        elif "TakerPaysCurrency" in node_fields:
            return "an offer Directory"
        else:
            return "a Directory node"
            
    if nodetype == "AccountRoot":
        return "the account %s" % lookup_acct(node_fields["Account"])
        
    #fallback, hopefully shouldn't reach here
    return "a %s node" % nodetype
    
    
def describe_node_changes(node):
    changes = []
    nodetype = node["LedgerEntryType"]
    if nodetype == "AccountRoot" and "PreviousFields" in node and "FinalFields" in node:
        if "Balance" in node["FinalFields"] and "Balance" in node["PreviousFields"]:
            prev_balance = drops_to_xrp(node["PreviousFields"]["Balance"])
            final_balance = drops_to_xrp(node["FinalFields"]["Balance"])
            diff = final_balance - prev_balance
            if diff > 0:
                changes.append("increasing its XRP balance by %f" % diff)
            else:
                changes.append("decreasing its XRP balance by %f" % -diff)
    if nodetype == "RippleState" and "PreviousFields" in node and "FinalFields" in node:
        ffields = node["FinalFields"]
        pfields = node["PreviousFields"]
        if "Balance" in ffields and "Balance" in pfields:
            prev_amount = pfields["Balance"]
            if is_string(prev_amount):
                prev_balance = drops_to_xrp(prev_amount)
                currency = "XRP"
            else:
                prev_balance = float(prev_amount["value"])
                currency = prev_amount["currency"]
            final_amount = ffields["Balance"]
            
            if is_string(prev_amount):
                final_balance = drops_to_xrp(prev_amount)
            else:
                final_balance = float(final_amount["value"])
            
            diff = final_balance - prev_balance
            
            # Each node holds funds issued by the other
            low_node = ffields["LowLimit"]["issuer"]
            high_node = ffields["HighLimit"]["issuer"]
            
            #perspective from the non-gateway account generally makes more sense
            if ffields["LowLimit"]["value"] > ffields["HighLimit"]["value"]:
                perspective_low = True
            elif final_balance > 0 or prev_balance > 0:
                perspective_low = True
            else:
                perspective_low = False
            
            if perspective_low:
                if diff > 0:
                    changes.append("increasing the amount %s holds by %f %s" % 
                        (lookup_acct(low_node), diff, currency))
                else:
                    changes.append("decreasing the amount %s holds by %f %s" % 
                        (lookup_acct(low_node), -diff, currency))
            else:
                if diff > 0:
                    changes.append("decreasing the amount %s holds by %f %s" % 
                        (lookup_acct(high_node), diff, currency))
                else:
                    changes.append("increasing the amount %s holds by %f %s" % 
                        (lookup_acct(high_node), -diff, currency))
            
    if not changes:
        return ""
        
    if len(changes) > 1:
        changes = [""]+changes[:-1]+["and "+changes[-1]]
        return ", ".join(changes)
    else:
        return ", "+changes[0]

    
def amount_to_string(amount, any_if=None):
    if is_string(amount):
        return "%f XRP" % drops_to_xrp(amount)
    else:
        if any_if == amount["issuer"]:
            # If SendMax issuer == source account, special case "use any"
            # If Amount issuer == destination account, same
            return "%s %s" % (amount["value"], amount["currency"])
        else:
            return "%s %s.%s" % (amount["value"], amount["currency"], lookup_acct(amount["issuer"], tilde=False))

    
def drops_to_xrp(drops):
    return int(drops) / 1000000.0


def fetch(tx_hash):
    command = {
        "method": "tx",
        "params": [
            {
                "transaction": tx_hash,
                "binary": False
            }
        ]
    }

    conn = httplib.HTTPConnection(RIPPLED_HOST, RIPPLED_PORT)
    conn.request("POST", "/", json.dumps(command))
    response = conn.getresponse()
    
    s = response.read()
    
    response_json = json.loads(s.decode("utf-8"))
    #s = json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': '))
    if "status" in response_json and response_json["status"]=="error":
        raise KeyError("tx not found")
    return response_json
    

known_acts = {}
def lookup_acct(address, tilde=True):
    global known_acts, tx_parties
    
    if address in known_acts:
        if "Unknown Account" not in known_acts[address]:
            tx_parties[address] = "~"+known_acts[address]
        else:
            tx_parties[address] = "Unknown Account"
            
        if tilde and "Unknown Account" not in known_acts[address]:
            return "~"+known_acts[address]
        else:
            return known_acts[address]
    
    url = "/v1/user/%s" % address
    conn = httplib.HTTPSConnection(RIPPLE_ID_HOST, RIPPLE_ID_PORT)
    conn.request("GET", url)
    response = conn.getresponse()
    
    s = response.read()
    response_json = json.loads(s.decode("utf-8"))
    
    if "username" in response_json:
        username = response_json["username"]
        tx_parties[address] = "~"+username
    else:
        tx_parties[address] = "Unknown Account"
        username = "%s (Unknown Account)" % address
    
    # Add it to known_acts so we don't have to http again
    known_acts[address] = username
    
    if tilde == True and "username" in response_json:
        return "~"+username
    else:
        return username


def lookup_ledger(ledger_index=0, ledger_hash=""):
    assert ledger_index or ledger_hash
    
    #You should probably not pass both, but this'll let
    # rippled decide what to do in that case.
    params = {
        "transactions": True
    }
    if ledger_index:
        params["ledger_index"] = ledger_index
    if ledger_hash:
        params["ledger_hash"] = ledger_hash
    
    command = {
        "method": "ledger",
        "params": [params]
    }

    conn = httplib.HTTPConnection(RIPPLED_HOST, RIPPLED_PORT)
    conn.request("POST", "/", json.dumps(command))
    response = conn.getresponse()

    s = response.read()

    response_json = json.loads(s.decode("utf-8"))
    if "result" in response_json and "ledger" in response_json["result"]:
        return response_json["result"]["ledger"]
    else:
        raise KeyError("Response from rippled doesn't have a ledger as expected")
    

# Looking up all the ripple names takes a long time. Save that shit!
def load_known_names(fname = PICKLE_FILE):
    global known_acts
    try:
        with open(fname, "rb") as f:
            known_acts = pickle.load(f)
    except:
        print("Info: Couldn't load names dictionary. This might be normal.")
    
    
def save_known_names(fname = PICKLE_FILE):
    global known_acts
    with open(fname, "wb") as f:
        pickle.dump(known_acts, f)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit("usage: %s tx_hash"%sys.argv[0])
        
    load_known_names()
    
    tx_hash = sys.argv[1]
    tx_json = fetch(tx_hash)["result"]
    print(splain(tx_json))
    
    save_known_names()
    
    

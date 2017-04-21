#!/bin/env python

from __future__ import print_function
import json, sys, pickle, struct, re
from warnings import warn
from datetime import datetime


# config constants -----------------------------

RIPPLED_HOST = "s2.ripple.com"
RIPPLED_PORT = 51234
RIPPLE_ID_HOST = "id.ripple.com"
RIPPLE_ID_PORT = 443
PICKLE_FILE = "ripnames.pkl"

# rippled constants ----------------------------
TX_FLAGS = {
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
    "SetFee": {},
    "EnableAmendment": {
        0x00010000: "tfGotMajority",
        0x00020000: "tfLostMajority",
    },
    "EscrowCancel": {},
    "EscrowCreate": {},
    "EscrowFinish": {},
    "PaymentChannelClaim": {
        0x00010000: "tfRenew",
        0x00020000: "tfClose"
    },
    "PaymentChannelCreate": {},
    "PaymentChannelFund": {}
}

LEDGER_FLAGS = {
    "AccountRoot": {
        0x00010000: "lsfPasswordSpent",
        0x00020000: "lsfRequireDestTag",
        0x00040000: "lsfRequireAuth",
        0x00080000: "lsfDisallowXRP",
        0x00100000: "lsfDisableMaster",
        0x00200000: "lsfNoFreeze",
        0x00400000: "lsfGlobalFreeze",
        0x00800000: "lsfDefaultRipple",
    },
    "RippleState": {
##      Reserve flags aren't set manually, so we check them specially
#        0x00010000: "lsfLowReserve",
#        0x00020000: "lsfHighReserve",
        0x00040000: "lsfLowAuth",
        0x00080000: "lsfHighAuth",
        0x00100000: "lsfLowNoRipple",
        0x00200000: "lsfHighNoRipple",
        0x00400000: "lsfLowFreeze",
        0x00800000: "lsfHighFreeze",
    },
    "Offer": {
        0x00010000: "lsfPassive",
        0x00020000: "lsfSell"
    }
}

AMENDMENTS = {
    "1562511F573A19AE9BD103B5D6B9E01B3B46805AEC5D3C4805C902B514399146": "CryptoConditions",
    "07D43DCE529B15A10827E5E04943B496762F9A88E3268269D69C44BE49E21104": "Escrow",
    "42426C4D4F1009EE67080A9B7965B44656D7714D104A72F9B4369F97ABF044EE": "FeeEscalation",
    "E2E6F2866106419B88C50045ACE96368558C345566AC8F2BDF5A5B5587F0E6FA": "fix1368",
    "740352F2412A9909880C23A559FCECEDA3BE2126FED62FC7660D628A06927F11": "Flow",
    "5CC22CFF2864B020BD79E0E1F048F63EF3594F95E650E43B3F837EF1DF5F4B26": "FlowV2",
    "4C97EBA926031A7CF7D7B36FDE3ED66DDA5421192D63DE53FFB46E43B9DC8373": "MultiSign",
    "9178256A980A86CF3D70D0260A7DA6402AAFE43632FDBCB88037978404188871": "OwnerPaysFee",
    "08DE7D96082187F6E6578530258C77FAABABE4C20474BDB82F04B021F1A68647": "PayChan",
    "C6970A8B603D8778783B61C0D445C23D1633CCFAEF0D43E7DBCD1521D34BD7C3": "SHAMapV2",
    "DA1BD556B42D85EA9C84066D028D355B52416734D3283F85E216EA5DA6DB7E13": "SusPay",
    "C1B8D934087225F509BEB5A8EC24447854713EE447D277F69545ABFA0E0FD490": "Tickets",
    "532651B4FD58DF8922A49BA101AB3E996E5BFBF95A913B3E392504863E63B164": "TickSize",
    "6781F8368C4771B83E8B821D88F580202BCB4228075297B19E4FDC5233F1EFDC": "TrustSetAuth",
}

PATHSTEP_RIPPLING = 0x01
PATHSTEP_REDEEMING = 0x02
PATHSTEP_ORDERBOOK = 0x10
PATHSTEP_ISSUER = 0x20

RIPPLE_EPOCH = 946684800#2000-01-01T00:00:00 UTC

# Python 2/3-agnostic stuff ----------------
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

def is_uint(s):
    try:
        if int(s) >= 0:
            return True
        else:
            return False
    except:
        return False

# basic utils -------------
def dumpjson(j):
    return json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))

# ripple utils ------------
def amount_to_string(amount, any_if=None):
    if is_string(amount):
        return "%f XRP" % drops_to_xrp(amount)
    else:
        if any_if == amount["issuer"]:
            # If SendMax issuer == source account, special case "use any"
            # If Amount issuer == destination account, same
            return "%s %s" % (amount["value"], amount["currency"])
        else:
            return "%s %s.%s" % (amount["value"], amount["currency"], lookup_rippleid(amount["issuer"], tilde=False))


def is_account_address(s):
    return re.match(
        "^r[rpshnaf39wBUDNEGHJKLM4PQRST7VWXYZ2bcdeCg65jkm8oFqi1tuvAxyz]{24,34}$",
        s.strip())

def is_ripple_name(s):
    return re.match("~[0-9A-Za-z]{3,20}", s.strip())

def is_hash256(s):
    return re.match("^[0-9A-F]{64}$", s.strip(), re.IGNORECASE)

def is_currency_code(s):
    return re.match("^[A-Z0-9]{3}$|^[0-9A-F]{40}$", s.strip())

def drops_to_xrp(drops):
    return int(drops) / 1000000.0

def quality_to_percent(quality):
    return quality / 10000000.0

def ripple_time_to_human(seconds):
    return datetime.utcfromtimestamp(seconds+RIPPLE_EPOCH).isoformat()+"Z"
    # Don't try this in 32-bit ints --------^


def json_rpc_call(method, params={}):
    """
    Connect to rippled's JSON-RPC API.
    - method: string, e.g. "account_info"
    - params: dictionary (JSON object),
        e.g. {"account": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
              "ledger" : "current"}
    """
    command = {
        "method": method,
        "params": [params]
    }

    conn = httplib.HTTPConnection(RIPPLED_HOST, RIPPLED_PORT)
    conn.request("POST", "/", json.dumps(command))
    response = conn.getresponse()

    s = response.read()

    response_json = json.loads(s.decode("utf-8"))
    if "result" in response_json:
        return response_json["result"]
    else:
        warn(response_json)
        raise KeyError("Response from rippled doesn't have result as expected")

def tx(tx_hash):
    """
    rippled tx command
    """
    params = {
        "transaction": tx_hash,
        "binary": False
    }
    tx = json_rpc_call("tx", params)

    if "status" in tx and tx["status"]=="error":
        raise KeyError("tx not found")
    return tx


def lookup_ledger(ledger_index=0, ledger_hash="", expand=False):
    assert ledger_index or ledger_hash

    #You should probably not pass both, but this'll let
    # rippled decide what to do in that case.
    params = {
        "transactions": True,
        "expand": expand
    }
    if ledger_index:
        params["ledger_index"] = ledger_index
    if ledger_hash:
        params["ledger_hash"] = ledger_hash

    result = json_rpc_call("ledger", params)

    if "ledger" in result:
        return result["ledger"]
    else:
        raise KeyError("Response from rippled doesn't have a ledger as expected")


def account_info(address, ledger_index="validated"):
    params = {
        "account": address,
        "ledger_index": ledger_index
    }
    result = json_rpc_call("account_info", params)

    if "account_data" in result:
        return result["account_data"]
    else:
        warn(str(result))
        raise KeyError("Response from rippled doesn't have account_data as expected")

def get_reserve_constants():
    result = json_rpc_call("server_info")
    vl = result["info"]["validated_ledger"]
    reserve_base = vl["reserve_base_xrp"]
    reserve_owner = vl["reserve_inc_xrp"]
    return reserve_base, reserve_owner

def lookup_trustline(address1, address2, currency, ledger_index="validated"):
    params = {
        "ripple_state": {
            "accounts": [address1, address2],
            "currency": currency
        },
        "ledger_index": ledger_index
    }
    result = json_rpc_call("ledger_entry", params)

    if "node" in result:
        return result["node"]
    else:
        raise KeyError("Response from rippled doesn't have the node as expected")

def lookup_offer(address, seq, ledger_index="validated"):
    params = {
        "offer": {
            "account": address,
            "seq": seq
        },
        "ledger_index": ledger_index
    }
    result = json_rpc_call("ledger_entry", params)

    if "node" in result:
        return result["node"]
    else:
        raise KeyError("Response from rippled doesn't have the node as expected")

# transaction splaining ------------------
tx_parties = {}
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
        for flag_bit,flag_name in TX_FLAGS["*"].items():
            if tx_json["Flags"] & flag_bit:
                enabled_flags.append(flag_name)
        for flag_bit,flag_name in TX_FLAGS[tx_type].items():
            if tx_json["Flags"] & flag_bit:
                enabled_flags.append(flag_name)

    if tx_type == "Payment":
        msg += "This is a Payment from %s to %s.\n" % (lookup_rippleid(tx_json["Account"]),
                lookup_rippleid(tx_json["Destination"]))
    elif tx_type == "OfferCreate":
        if "tfSell" in enabled_flags:
            msg += "This is an OfferCreate, where %s offered to pay %s in order to receive at least %s.\n" % (
                    lookup_rippleid(tx_json["Account"]), amount_to_string(tx_json["TakerGets"]),
                    amount_to_string(tx_json["TakerPays"]) )
        else:
            msg += "This is an OfferCreate, where %s offered to pay up to %s in order to receive %s.\n" % (
                    lookup_rippleid(tx_json["Account"]), amount_to_string(tx_json["TakerGets"]),
                    amount_to_string(tx_json["TakerPays"]) )
        if "OfferSequence" in tx_json:
            msg += "Additionally, it was intended to cancel a previous offer with sequence #%d.\n" % tx_json["OfferSequence"]
    elif tx_type == "EscrowCreate":
        msg += "This is an EscrowCreate transaction, where %s attempted to create a held payment of %s to %s.\n" % (
                lookup_rippleid(tx_json["Account"]),
                amount_to_string(tx_json["Amount"]),
                lookup_rippleid(tx_json["Destination"]), )
        if "CancelAfter" in tx_json:
            msg += "The held payment expires at %s.\n" % (
                    ripple_time_to_human(tx_json["CancelAfter"]))
        if "FinishAfter" in tx_json:
            msg += "The payment is held until %s.\n" % (
                    ripple_time_to_human(tx_json["FinishAfter"]))
        if "Condition" in tx_json:
            msg += "The held payment is contingent on a crypto-condition.\n"
    elif tx_type == "PaymentChannelCreate":
        msg += "This is an PaymentChannelCreate transaction, where %s attempted to create a payment channel to %s with %s.\n" % (
                lookup_rippleid(tx_json["Account"]),
                lookup_rippleid(tx_json["Destination"]),
                lookup_rippleid(tx_json["Amount"]))
        msg += "The SettleDelay before this channel be closed is %s seconds." % (
                tx_json["SettleDelay"])
        if "CancelAfter" in tx_json:
            msg += "The channel expires at %s.\n" % (
                    ripple_time_to_human(tx_json["CancelAfter"]))
    elif tx_type == "SetFee":
        msg += "This is a SetFee pseudo-transaction.\n"
    elif tx_type == "EnableAmendment":
        msg += "This is an EnableAmendment pseudo-transaction for %s.\n" % (
                    AMENDMENTS.get(tx_json["Amendment"], "an unknown Amendment"))
    elif tx_type == "EscrowFinish":
        msg += ("This is an EscrowFinish transaction, sent by %s, to execute "+ 
                "the held payment created by %s's transaction with sequence "+
                "number %s.\n") % (lookup_rippleid(tx_json["Account"]),
                    lookup_rippleid(tx_json["Owner"]),
                    tx_json["OfferSequence"] )
        if "Fulfillment" in tx_json:
            msg += "It specified the fulfillment %s.\n" % tx_json["Fulfillment"]
    else:
        msg += "This is a %s transaction.\n" % tx_type
        msg += "The transaction was sent by %s.\n" % lookup_rippleid(tx_json["Account"])

    if "DestinationTag" in tx_json:
        msg += "The transaction specified the Destination Tag %s.\n" % tx_json["DestinationTag"]

    if "SourceTag" in tx_json:
        msg += "The transaction specified the Source Tag %s.\n" % tx_json["SourceTag"]

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
                if node["LedgerEntryType"] == "Offer" and "PreviousFields" in node:
                    #If the offer is deleted for being unfunded or canceled, there are no PreviousFields
                    msg += "..  It consumed %s.\n" % describe_node(node)
                else:
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
        if addr != alias:
            s += ".. %s: %s\n" % (addr, alias)
        else:
            s += ".. %s\n"
    return s

def describe_paths(pathset):
    msg = "It specified %d paths other than the default one:\n" % len(pathset)
    for path in pathset:
        ptext = "Source - "
        for step in path:
            if step["type"] & PATHSTEP_ORDERBOOK:
                if step["type"] & PATHSTEP_ISSUER:
                    currency = "%s.%s" % (step["currency"],
                            lookup_rippleid(step["issuer"], tilde=False))
                else:
                    currency = step["currency"]
                ptext += "Orderbook:%s - " % step["currency"]
            if step["type"] & PATHSTEP_RIPPLING:
                ptext += "%s - " % lookup_rippleid(step["account"])
        ptext += "Destination"
        msg += "..  %s\n" % ptext

    return msg


def describe_node(node):
    nodetype = node["LedgerEntryType"]
    # DeletedNode/ModifiedNode have FinalFields; CreateNode has NewFields
    new_fields = {}
    prev_fields = {}
    final_fields = {}
    node_fields = {}
    if "NewFields" in node:
        node_fields = node["NewFields"]
        new_fields = node["NewFields"]
    if "PreviousFields" in node:
        node_fields = node["PreviousFields"]
        prev_fields = node["PreviousFields"]
    if "FinalFields" in node:
        node_fields = node["FinalFields"]
        final_fields = node["FinalFields"]

    if nodetype == "Offer":
        #prefer Prev fields if possible, since that better indicates the status of consumed offers
        if "TakerPays" in prev_fields and "TakerGets" in prev_fields:
            taker_pays = prev_fields["TakerPays"]
            taker_gets = prev_fields["TakerGets"]
        elif "TakerPays" in new_fields and "TakerGets" in new_fields:
            taker_pays = new_fields["TakerPays"]
            taker_gets = new_fields["TakerGets"]
        elif "TakerPays" in final_fields and "TakerGets" in final_fields:
            taker_pays = final_fields["TakerPays"]
            taker_gets = final_fields["TakerGets"]
        else:
            #probably shouldn't get here, but handle it gracefully
            return "%s's Offer" % lookup_rippleid(node_fields["Account"])

        return "%s's Offer (seq#%s) to buy %s for %s" % (
                    lookup_rippleid(node_fields["Account"]),
                    node_fields["Sequence"],
                    amount_to_string(taker_pays), amount_to_string(taker_gets))


    if nodetype == "RippleState":
        return "the trust line between %s and %s" % (
                lookup_rippleid(node_fields["HighLimit"]["issuer"]),
                lookup_rippleid(node_fields["LowLimit"]["issuer"]))

    if nodetype == "DirectoryNode":
        if "Owner" in node_fields:
            return "a Directory owned by %s" % lookup_rippleid(node_fields["Owner"])
        elif "TakerPaysCurrency" in node_fields:
            return "an offer Directory"
        else:
            return "a Directory node"

    if nodetype == "AccountRoot":
        if "Account" in node_fields:
            return "the account %s" % lookup_rippleid(node_fields["Account"])
        else:
            # Strangely, sometimes you get a ModifiedNode with no such field
            return "the account with ledger node index %s" % node["LedgerIndex"]

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
                        (lookup_rippleid(low_node), diff, currency))
                else:
                    changes.append("decreasing the amount %s holds by %f %s" %
                        (lookup_rippleid(low_node), -diff, currency))
            else:
                if diff > 0:
                    changes.append("decreasing the amount %s holds by %f %s" %
                        (lookup_rippleid(high_node), diff, currency))
                else:
                    changes.append("increasing the amount %s holds by %f %s" %
                        (lookup_rippleid(high_node), -diff, currency))

    if not changes:
        return ""

    if len(changes) > 1:
        changes = [""]+changes[:-1]+["and "+changes[-1]]
        return ", ".join(changes)
    else:
        return ", "+changes[0]


# account splaining -------------------------

def splain_account(account):
    address = account["Account"]
    s = "This is account %s" % address
    name = lookup_rippleid(address)
    if "~" not in known_acts[address]:
        s += ", which has no Ripple Name.\n"
    else:
        s += ", which has Ripple Name %s.\n" % name

    s += "It has %f XRP.\n" % drops_to_xrp(account["Balance"])
    s += "It owns %d objects in the ledger, which means its reserve is %d XRP.\n" % \
            (account["OwnerCount"], calculate_reserve(account["OwnerCount"]))

    flags = account["Flags"]
    enabled_flags = []
    if not flags:
        s += "It has no flags enabled.\n"
    else:
        for flag_bit,flag_name in LEDGER_FLAGS["AccountRoot"].items():
            if flags & flag_bit:
                enabled_flags.append(flag_name)
        s += "It has the following flags enabled: %s.\n" % \
                ", ".join(enabled_flags)

    if "PreviousTxnLgrSeq" in account and "PreviousTxnID" in account:
        s += "This node was last modified by Transaction %s" % account["PreviousTxnID"]
        try:
            previoustxn_ledger = lookup_ledger(account["PreviousTxnLgrSeq"])
            s += " in ledger %d, on %s.\n" % (account["PreviousTxnLgrSeq"],
                    previoustxn_ledger["close_time_human"])
        except KeyError:
            s += " in ledger %d.\n" % account["PreviousTxnLgrSeq"]
        s += "(Its trust lines might have been modified more recently.)\n"

    if "AccountTxnID" in account:
        s += "It has AccountTxnID enabled. "
        s += "Its most recently sent transaction is %s.\n" % account["AccountTxnID"]

    if "Domain" in account:
        s += "It refers the following domain: %s\n" % decode_hex(account["Domain"])

    if "urlgravatar" in account:
        s += "Avatar: %s\n" % account["urlgravatar"]

    if "TransferRate" in account and account["TransferRate"] != 0 and \
            account["TransferRate"] != 1000000000:
        s += "It has a transfer fee of %f%%.\n" % \
                calculate_transfer_fee(account["TransferRate"])

    if "MessageKey" in account:
        s += "To send an encrypted message to this account, you should encode it with public key %s.\n" % account["MessageKey"]

    s = parties() + s

    return s

def calculate_transfer_fee(transfer_rate):
    return ( (transfer_rate / 1000000000.0) - 1) * 100 #percent

def calculate_reserve(owner_count):
    reserve_base, reserve_owner = get_reserve_constants()
    return reserve_base + (owner_count * reserve_owner)

# trust line splaining----------------------------------------

def splain_trust_line(trustline):
    currency = trustline["Balance"]["currency"]
    balance = trustline["Balance"]["value"]
    lownode = trustline["LowLimit"]["issuer"]
    highnode = trustline["HighLimit"]["issuer"]
    lowlimit = trustline["LowLimit"]["value"]
    highlimit = trustline["HighLimit"]["value"]
    lowname = lookup_rippleid(lownode)
    highname = lookup_rippleid(highnode)

    s = "This is a %s trust line between %s and %s.\n" % (currency, lowname, highname)
    s += "%s is considered the low node, and %s is considered the high node.\n" % (lowname, highname)
    if float(balance) < 0:
        #the low node owes money to the high node
        s += "%s currently possesses %f %s issued by %s, out of a limit of %s %s.\n" % (highname,
                -float(balance), currency, lowname, highlimit, currency)
        s += "%s is willing to hold up to %s %s on this trust line.\n" % (lowname,
            lowlimit, currency)
    else:
        s += "%s currently possesses %s %s issued by %s, out of a limit of %s %s.\n" % (lowname,
                balance, currency, highname, lowlimit, currency)
        s += "%s is willing to hold up to %s %s on this trust line.\n" % (highname,
            highlimit, currency)


    flags = trustline["Flags"]
    low_enabled_flags = []
    high_enabled_flags = []
    for flag_bit,flag_name in LEDGER_FLAGS["RippleState"].items():
        if flags & flag_bit:
            if "Low" in flag_name:
                low_enabled_flags.append(flag_name)
            elif "High" in flag_name:
                high_enabled_flags.append(flag_name)
            else:
                warn("Unrecognized flag: %s" % flag_name)
    if low_enabled_flags:
        s += "%s has enabled the following flags: %s.\n" % ( lowname,
                ", ".join(low_enabled_flags) )
    else:
        s += "%s has not enabled any flags for this trust line.\n" % lowname
    if high_enabled_flags:
        s += "%s has enabled following flags: %s.\n" % ( highname,
                ", ".join(high_enabled_flags) )
    else:
        s += "%s has not enabled any flags for this trust line.\n" % highname

    lsfLowReserve = 0x00010000
    lsfHighReserve = 0x00020000
    if flags & lsfLowReserve:
        s += "This trust line contributes to %s's owner reserve.\n" % lowname
    if flags & lsfHighReserve:
        s += "This trust line contributes to %s's owner reserve.\n" % highname

    if "LowQualityIn" in trustline:
        s += "%s values incoming amounts on this trust line at %f%% of face value.\n" % (
                lowname, quality_to_percent(trustline["LowQualityIn"]) )
    if "LowQualityOut" in trustline:
        s += "%s values outgoing amounts on this trust line at %f%% of face value.\n" % (
                lowname, quality_to_percent(trustline["LowQualityOut"]) )
    if "HighQualityIn" in trustline:
        s += "%s values incoming amounts on this trust line at %f%% of face value.\n" % (
                highname, quality_to_percent(trustline["HighQualityIn"]) )
    if "HighQualityOut" in trustline:
        s += "%s values outgoing amounts on this trust line at %f%% of face value.\n" % (
                highname, quality_to_percent(trustline["HighQualityOut"]) )

    if "LowNode" in trustline and is_uint(trustline["LowNode"]):
        s += "This node is listed in page %d of %s's owner directory.\n" % (
                int(trustline["LowNode"]),
                lowname)
    if "HighNode" in trustline and is_uint(trustline["HighNode"]):
        s += "This node is listed in page %d of %s's owner directory.\n" % (
                int(trustline["HighNode"]),
                highname)

    s = parties() + s
    return s

# offer splaining ---------------------------

def splain_offer(offer):
    owner = lookup_rippleid(offer["Account"])

    enabled_flags = []
    for flag_bit,flag_name in LEDGER_FLAGS["Offer"].items():
        if offer["Flags"] & flag_bit:
            enabled_flags.append(flag_name)
    if "lsfSell" in enabled_flags:
        s = "This is an Offer (#%d) from %s to pay %s in order to receive at least %s.\n" % (
                    offer["Sequence"],
                    owner,
                    amount_to_string(offer["TakerGets"]),
                    amount_to_string(offer["TakerPays"]) )
    else:
        s = "This is an Offer (#%d) from %s to pay up to %s in order to receive %s.\n" % (
                    offer["Sequence"],
                    owner,
                    amount_to_string(offer["TakerGets"]),
                    amount_to_string(offer["TakerPays"]) )
    if enabled_flags:
        s += "It has the following flags enabled: %s.\n" % \
                ", ".join(enabled_flags)
    else:
        s += "It has no flags enabled.\n"

    if "OwnerNode" in offer and is_uint(offer["OwnerNode"]):
        s += "This offer is listed in page %d of %s's owner directory.\n" % (
                int(offer["OwnerNode"]),
                owner)
    if "BookDirectory" in offer:
        if "BookNode" in offer and is_uint(offer["BookNode"]):
            s += "This offer is listed in page %d of Offer Directory %s.\n" % (
                    int(offer["BookNode"]), offer["BookDirectory"])
        else:
            s += "This offer is listed in Offer Directory %s.\n" % offer["BookDirectory"]

    validated_ledger = lookup_ledger(ledger_index="validated")
    if "Expiration" in offer:
        if validated_ledger["close_time"] > offer["Expiration"]:
            s += "This offer has passed its expiration time of %s.\n" % ripple_time_to_human(offer["Expiration"])
        else:
            s += "This offer will expire if not claimed before a ledger closes with time > %s.\n" % ripple_time_to_human(offer["Expiration"])

    s = parties() + s
    return s

# rippleid utils ----------------------------
known_acts = {}
def lookup_rippleid(address, tilde=True):
    global known_acts, tx_parties

    if address in known_acts:
        if "~" not in known_acts[address]:
            tx_parties[address] = "Unknown Account"
        else:
            tx_parties[address] = known_acts[address]

        # only return a tilde if requested AND a name
        if not tilde:
            return known_acts[address].replace("~","")
        else:
            return known_acts[address]

    #print("looking up %s" % address)
    url = "/v1/user/%s" % address
    conn = httplib.HTTPSConnection(RIPPLE_ID_HOST, RIPPLE_ID_PORT)
    conn.request("GET", url)
    response = conn.getresponse()

    s = response.read()
    response_json = json.loads(s.decode("utf-8"))

    if "exists" in response_json and response_json["exists"]:
        username = "~"+response_json["username"]
        tx_parties[address] = "~"+username
        has_name = True
    else:
        tx_parties[address] = "Unknown Account"
        username = address
        has_name = False

    # Add it to known_acts so we don't have to http again
    known_acts[address] = username

    if not tilde:
        return username.replace("~","")
    else:
        return username

def lookup_ripple_address(name):
    global known_acts
    #strip leading tilde
    if name[0] == "~":
        name = name[1:]

    def inverse_lookup(needle, haystack):
        for key,value in haystack.items():
            if value == needle:
                return key

        raise KeyError

    try:
        address = inverse_lookup(name, known_acts)
        return address
    except KeyError:
        pass #gonna have to look it up below


    #print("looking up %s" % name)
    url = "/v1/user/%s" % name
    conn = httplib.HTTPSConnection(RIPPLE_ID_HOST, RIPPLE_ID_PORT)
    conn.request("GET", url)
    response = conn.getresponse()

    s = response.read()
    response_json = json.loads(s.decode("utf-8"))

    if "address" in response_json:
        address = response_json["address"]
        known_acts[address] = name
        return address
    else:
        raise KeyError

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


# commandline operation ------------------------------
if __name__ == "__main__":
    USAGE_MESSAGE = "Proper usage:\nGet transaction:\n  %s tx_hash\nGet account:\n  %s account_address\nGet trust line:\n  %s address1 address2 currency\nGet order:\n  %s account_address order_sequence" % ((sys.argv[0],)*4)

    if len(sys.argv) <2 or len(sys.argv)>4:
        exit(USAGE_MESSAGE)

    if len(sys.argv) == 2:
        #either a tx hash or an account address

        load_known_names()

        arg1 = sys.argv[1]
        if is_account_address(arg1):
            acct_json = account_info(arg1)
            print(splain_account(acct_json))
        elif is_hash256(arg1):
            tx_json = tx(arg1)
            print(splain(tx_json))
        elif is_ripple_name(arg1):
            try:
                address = lookup_ripple_address(arg1)
            except KeyError:
                print("Ripple Name %s not found." % arg1)
                exit()

            acct_json = account_info(address)
            print(splain_account(acct_json))
        else:
            exit(USAGE_MESSAGE)

        save_known_names()

    if len(sys.argv) == 3:
        #address + seq = offer

        load_known_names()

        if is_account_address(sys.argv[1]) and is_uint(sys.argv[2]):
            offer = lookup_offer(sys.argv[1], int(sys.argv[2]))
            print(splain_offer(offer))
        else:
            exit(USAGE_MESSAGE)

    if len(sys.argv) == 4:
        # address1 + address2 + currency = trust line

        load_known_names()

        if is_account_address(sys.argv[1]) and is_account_address(sys.argv[2]) and is_currency_code(sys.argv[3]):
            trustline = lookup_trustline(sys.argv[1], sys.argv[2], sys.argv[3])
            print(splain_trust_line(trustline))
        else:
            exit(USAGE_MESSAGE)

        save_known_names()

TXSPLAIN
========

`txsplain.py` is a simple Python (2/3) script that takes a Ripple transaction hash as input, looks up the transaction using JSON-RPC, and generates a human-readable explanation of the transaction data. Features include:

* Ripple Name lookup for addresses in the transaction (including local caching of names for faster lookups).
* Decipher flags relative to transaction type.
* Detect success or failure and validation state for all transactions.
* Display actual delivered amount (when `delivered_amount` field is available) for payments.
* Describe Paths included in the transaction.
* Converts from wire format XRP "Drops" to human-readable XRP values.
* Describe changes to affected nodes in transaction metadata.
* Detect and read Ripple Trade client IDs from `Memos` field.

Example usage:
---------------
```
$ ./txsplain.py E485D1E18D946ACD410AD79F51E2C57E887CC206286E6CE0A1CA80FC75C24643 
{
    "Account": "rBvktWhzs4MQDaFYScsqPCB5YufRDXwKDC",
    "Amount": "600000000000",
    "Destination": "rBvktWhzs4MQDaFYScsqPCB5YufRDXwKDC",
    "Fee": "12000",
    /* ... snip ... */
    "status": "success",
    "validated": true
}


This is a Payment from ~ootomo to ~ootomo.
The transaction used no flags.
Sending this transaction consumed 0.012000 XRP.
The transaction was successful.
This result has been validated by consensus, in ledger 11547185.
It was instructed to deliver 600000.000000 XRP by spending up to 1166313.057 JPY.tokyojpy.
It actually delivered 600000.000000 XRP.
A memo indicates it was sent with the client 'rt1.3.1'.
It specified 1 paths other than the default one:
  Source - Orderbook:XRP - Destination
It affected 102 nodes in the global ledger, including:
  It modified a Directory owned by ~taiken0314.
  It modified ~ccudjs's Offer to buy 599999.997 JPY.tokyojpy for 300000.000000 XRP.
  It deleted ~toshio-san's Offer to buy 9067 JPY.tokyojpy for 4698.270297 XRP.
  It modified the account ~King-Mularkey, decreasing its XRP balance by 590.765131.
  It modified the account ~i9p1a6p6, decreasing its XRP balance by 123528.580381.
  It modified the trust line between ~ootomo and ~tokyojpy, decreasing the amount ~ootomo holds by 1164533.852421 JPY.
  It deleted ~ytrade123's Offer to buy 13451.575 JPY.tokyojpy for 7103.776758 XRP.
  It modified a Directory owned by ~ripple0825.
  It modified a Directory owned by ~i9p1a6p6.
  It modified a Directory owned by ~tokyojpy.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It deleted an offer Directory.
  It modified a Directory owned by ~donPewoqu.
  It modified a Directory owned by ~jshfineboy.
  It deleted ~cofe89's Offer to buy 2500 JPY.tokyojpy for 1283.367556 XRP.
  It modified a Directory owned by ~goodmeatarai.
  It modified the account rH5wSLPotxA4kfTcAyZiBfqbdCWCBM8ape (Unknown Account), decreasing its XRP balance by 9867.801059.
  It modified a Directory owned by ~yangkun5088.
  It deleted ~donPewoqu's Offer to buy 20000 JPY.tokyojpy for 10396.800000 XRP.
  It modified the account ~yangkun5088, decreasing its XRP balance by 121123.019295.
  It modified the account ~jshfineboy, decreasing its XRP balance by 5501.221572.
  It modified the trust line between ~GoldsmithX and ~tokyojpy, increasing the amount ~GoldsmithX holds by 46674.651000 JPY.
  It modified the account ~taiken0314, decreasing its XRP balance by 50000.000000.
  It modified the trust line between ~ytrade123 and ~tokyojpy, increasing the amount ~ytrade123 holds by 13451.575000 JPY.
  It modified the account ~goodmeatarai, decreasing its XRP balance by 9847.131446.
  It modified a Directory owned by rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account).
  It modified the trust line between ~jshfineboy and ~tokyojpy, increasing the amount ~jshfineboy holds by 10766.140303 JPY.
  It deleted ~jshfineboy's Offer to buy 10766.140302676 JPY.tokyojpy for 5501.221572 XRP.
  It modified the account rajDteRmFXXs8ALEhfPpwMZy7QuW3o7MtE (Unknown Account), decreasing its XRP balance by 8475.183289.
  It deleted ~ripple0825's Offer to buy 13947.5 JPY.tokyojpy for 7000.000000 XRP.
  It deleted ~yangkun5088's Offer to buy 199992 JPY.tokyojpy for 100000.000000 XRP.
  It deleted rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account)'s Offer to buy 29573.06601819281 JPY.tokyojpy for 15637.788184 XRP.
  It deleted ~taiken0314's Offer to buy 98000 JPY.tokyojpy for 50000.000000 XRP.
  It modified the trust line between ~yangkun5088 and ~tokyojpy, increasing the amount ~yangkun5088 holds by 242235.926288 JPY.
  It modified the trust line between ~tokyojpy and ~taiken0314, increasing the amount ~taiken0314 holds by 98000.000000 JPY.
  It modified the account ~ccudjs, decreasing its XRP balance by 35166.068629.
  It modified the account ~ripple0825, decreasing its XRP balance by 6292.813650.
  It deleted ~yOdwaE's Offer to buy 67605.3 JPY.tokyojpy for 34300.000000 XRP.
  It deleted ~donPewoqu's Offer to buy 17838.82142594324 JPY.tokyojpy for 9444.603454 XRP.
  It created the trust line between ~yOdwaE and ~tokyojpy.
  It modified a Directory owned by ~toshio-san.
  It modified the account ~toshio-san, decreasing its XRP balance by 4698.270297.
  It modified the trust line between rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account) and ~tokyojpy, increasing the amount rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account) holds by 204480.086216 JPY.
  It modified the trust line between ~cofe89 and ~tokyojpy, increasing the amount ~cofe89 holds by 2500.000000 JPY.
  It modified a Directory owned by rajDteRmFXXs8ALEhfPpwMZy7QuW3o7MtE (Unknown Account).
  It deleted ~donPewoqu's Offer to buy 13180.70386476548 JPY.tokyojpy for 7063.895080 XRP.
  It modified a Directory owned by ~cofe89.
  It modified a Directory owned by ~satomi.
  It modified a Directory owned by ~GoldsmithX.
  It deleted rajDteRmFXXs8ALEhfPpwMZy7QuW3o7MtE (Unknown Account)'s Offer to buy 16667.91715521161 JPY.tokyojpy for 8475.183289 XRP.
  It modified the trust line between ~tokyojpy and ~ccudjs, increasing the amount ~ccudjs holds by 70332.136906 JPY.
  It modified the account ~cofe89, decreasing its XRP balance by 1283.367556.
  It deleted ~King-Mularkey's Offer to buy 97000 JPY.tokyojpy for 50000.000000 XRP.
  It modified a Directory owned by rH5wSLPotxA4kfTcAyZiBfqbdCWCBM8ape (Unknown Account).
  It deleted ~yangkun5088's Offer to buy 42243.9262880705 JPY.tokyojpy for 21123.019295 XRP.
  It modified the account ~satomi, decreasing its XRP balance by 25641.025641.
  It deleted ~i9p1a6p6's Offer to buy 229818.9815349562 JPY.tokyojpy for 123558.592222 XRP.
  It modified the trust line between ~tokyojpy and ~goodmeatarai, increasing the amount ~goodmeatarai holds by 19595.791577 JPY.
  It modified the account ~yOdwaE, decreasing its XRP balance by 34300.000000.
  It modified a Directory owned by ~ytrade123.
  It modified the trust line between ~tokyojpy and ~King-Mularkey, increasing the amount ~King-Mularkey holds by 1146.084354 JPY.
  It deleted rH5wSLPotxA4kfTcAyZiBfqbdCWCBM8ape (Unknown Account)'s Offer to buy 18690.12762354668 JPY.tokyojpy for 9867.801059 XRP.
  It modified a Directory owned by ~donPewoqu.
  It modified the trust line between ~toshio-san and ~tokyojpy, increasing the amount ~toshio-san holds by 9067.000000 JPY.
  It deleted ~goodmeatarai's Offer to buy 19595.79157740638 JPY.tokyojpy for 9847.131446 XRP.
  It created the trust line between rH5wSLPotxA4kfTcAyZiBfqbdCWCBM8ape (Unknown Account) and ~tokyojpy.
  It deleted ~satomi's Offer to buy 50000 JPY.tokyojpy for 25641.025641 XRP.
  It deleted rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account)'s Offer to buy 174907.0201980774 JPY.tokyojpy for 90688.888578 XRP.
  It modified the trust line between ~satomi and ~tokyojpy, increasing the amount ~satomi holds by 50000.000000 JPY.
  It modified the account ~ootomo, increasing its XRP balance by 599999.988000.
  It modified a Directory owned by ~donPewoqu.
  It modified a Directory owned by ~yOdwaE.
  It modified a Directory owned by ~King-Mularkey.
  It modified the account ~ytrade123, decreasing its XRP balance by 7103.776758.
  It deleted ~GoldsmithX's Offer to buy 46674.651 JPY.tokyojpy for 23349.000000 XRP.
  It modified the trust line between ~tokyojpy and ~i9p1a6p6, increasing the amount ~i9p1a6p6 holds by 229763.159509 JPY.
  It modified the account rK5j9n8baXfL4gzUoZsfxBvvsv97P5swaV (Unknown Account), decreasing its XRP balance by 106326.676762.
  It modified the trust line between ~ripple0825 and ~tokyojpy, increasing the amount ~ripple0825 holds by 12538.431198 JPY.
  It modified the trust line between ~tokyojpy and rajDteRmFXXs8ALEhfPpwMZy7QuW3o7MtE (Unknown Account), increasing the amount rajDteRmFXXs8ALEhfPpwMZy7QuW3o7MtE (Unknown Account) holds by 16667.917155 JPY.
  It modified the account ~tokyojpy.
  It modified the account ~donPewoqu, decreasing its XRP balance by 26905.298534.
  It modified the trust line between ~donPewoqu and ~tokyojpy, increasing the amount ~donPewoqu holds by 51019.525291 JPY.
  It modified the account ~GoldsmithX, decreasing its XRP balance by 23349.000000.
```

Account Lookup
--------------

txsplain can also be used to look up accounts. (This feature is not built into the Slackbot yet.) This includes:

* Ripple Name lookup
* Calculating the account's total reserve requirement
* Parsing any account flags currently enabled
* Explaining the other fields of the AccountRoot object

Example:

```
$ ./txsplain.py rf1BiGeXwwQoi8Z2ueFYTEXSwuJYfV2Jpn
This is account rf1BiGeXwwQoi8Z2ueFYTEXSwuJYfV2Jpn, which has Ripple Name ~Reginelli.
It has 148.446663 XRP.
It owns 3 objects in the ledger, which means its reserve is 35 XRP.
It has the following flags enabled: lsfDefaultRipple.
This node was last modified by Transaction 0D5FB50FA65C9FE1538FD7E398FFFE9D1908DFA4576D8D7A020040686F93C77D in ledger 14091160, on 2015-Jun-16 21:32:40.
(Its trust lines might have been modified more recently.)
It has AccountTxnID enabled. Its most recently sent transaction is 0D5FB50FA65C9FE1538FD7E398FFFE9D1908DFA4576D8D7A020040686F93C77D.
It refers the following domain: mduo13.com
Avatar: http://www.gravatar.com/avatar/98b4375e1d753e5b91627516f6d70977
It has a transfer fee of 0.500000%.
To send an encrypted message to this account, you should encode it with public key 0000000000000000000000070000000300.
```

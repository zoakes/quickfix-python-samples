#!/usr/bin/python
# -*- coding: utf8 -*-
"""FIX Application"""
import sys
import quickfix as fix
import time
import logging
from datetime import datetime
from model.logger import setup_logger
__SOH__ = chr(1)

# Logger
setup_logger('logfix', 'Logs/message.log')
logfix = logging.getLogger('logfix')


class Application(fix.Application):
    """FIX Application"""
    execID = 0

    def onCreate(self, sessionID):
        print("onCreate : Session (%s)" % sessionID.toString())
        return

    def onLogon(self, sessionID):
        self.sessionID = sessionID
        print("Successful Logon to session '%s'." % sessionID.toString())
        return

    def onLogout(self, sessionID):
        print("Session (%s) logout !" % sessionID.toString())
        return

    def toAdmin(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Admin) S >> %s" % msg)
        return
    def fromAdmin(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(Admin) R << %s" % msg)
        return

    ## Trades TO Server...
    def toApp(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(App) S >> %s" % msg)
        return

    ## FILLS from server...
    def fromApp(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.info("(App) R << %s" % msg)
        self.onMessage(message, sessionID)
        return

    ## HANDLE fills here !!
    def onMessage(self, message, sessionID):
        """Processing application message here"""
        #Process ExecutionReport !!

        beginString = fix.BeginString()
        msgType = fix.MsgType()
        message.getHeader().getField( beginString )
        message.getHeader().getField( msgType )

        symbol = fix.Symbol()
        side = fix.Side()
        # ordType = fix.OrdType() ##THIS is not in ExecutionReport !
        orderQty = fix.OrderQty()
        price = fix.Price()
        clOrdID = fix.ClOrdID()

        print(symbol)

        ## THIS is how you GET a value from a message... OR is it received like passed by ref in C++? Cant tell...

        # THIS canbe set to ANY field in ExecReport !! Test them all.

        field = symbol                              # 55=
        message.getField( field )                   # 55=MSFT
        if field.getValue() != fix.OrdType_LIMIT:   # MSFT != 1
            #raise fix.IncorrectTagValue( ordType.getField() )
            pass
            print("field (test) -- ", field, field.getValue())

        # Shortcut


        exec_type = fix.ExecType()
        message.getField( exec_type )
        if exec_type.getValue() != fix.ExecType_FILL:
            print("NOT filled...")
        else:
            print("< Order Filled >")


        leaves_qty = fix.LeavesQty()
        message.getField(leaves_qty)
        shares_rem = leaves_qty.getValue()
        if leaves_qty.getValue() != 0:
            print(" Shares Remaining -- {shares_rem}")
        else:
            print(" 0 Shares Remaining.")



        # ## THIS is the response type... (THIS is whats being SENT back to us)
        # if msgType == fix.MsgType_ExecutionReport:
        #     print("Fill Report Received...")

        ##executionReport.getHeader().setField( fix.MsgType(fix.MsgType_ExecutionReport) )


        # Remainign quantity (THIS is what is SENT to us... so parse it)
        # if beginString.getValue() >= fix.BeginString_FIX41:
        #     executionReport.setField( fix.ExecType(fix.ExecType_FILL) )
        #     executionReport.setField( fix.LeavesQty(0) )

        # if beginString.getValue() >= fix.BeginString_FIX41:
        #     message.getField( fix.ExecType()) # want fix.ExecType_FILL for FILL
        #     #rem = message.getField( fix.LeavesQty )
        #     #print(rem)



    def genExecID(self):
    	self.execID += 1
    	return str(self.execID).zfill(5)

    def put_new_order(self):
        """Request sample new order single"""
        message = fix.Message()
        header = message.getHeader()

        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle)) #39 = D 

        message.setField(fix.ClOrdID(self.genExecID())) #11 = Unique Sequence Number
        message.setField(fix.Side(fix.Side_BUY)) #43 = 1 BUY 
        message.setField(fix.Symbol("MSFT")) #55 = MSFT
        message.setField(fix.OrderQty(10000)) #38 = 1000
        message.setField(fix.Price(100))
        message.setField(fix.OrdType(fix.OrdType_LIMIT)) #40=2 Limit Order 
        message.setField(fix.HandlInst(fix.HandlInst_MANUAL_ORDER_BEST_EXECUTION)) #21 = 3
        message.setField(fix.TimeInForce('0'))
        message.setField(fix.Text("NewOrderSingle"))
        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3])
        message.setField(trstime)

        fix.Session.sendToTarget(message, self.sessionID)

    def send_order(self, symbol, side, qty, _price=None, _type='MKT'):
        message = fix.Message()
        header = message.getHeader()

        # DOES this need SELL or SELLSHORT ? Or BOTH?
        direction = fix.Side_BUY if side > 0 else fix.Side_SELL ##43 = 1 buy, or 2 sell (?) (MIGHT need sellshort + sell?)

        order_type = fix.OrdType_MARKET
        if _price:
            if _type.upper() == 'LMT':
                order_type = fix.OrdType_LIMIT

            elif _type.upper() == 'STP':
                order_type = fix.OrdType_STOP

            elif _type.upper() == 'MKT':
                order_type = fix.OrdType_MARKET

            elif _price.upper() == 'STPLMT':
                order_type = fix.OrdType_STOP_LIMIT
            else:
                raise Exception(f"Order Type Not Supported -- Got:  '{_type}', Expected ['LMT', 'STP', 'MKT']")

            # Add safety later (to ensure price matches WRT order type (Above limit, Below stop)
            # if _price:
            #     price = _price

        header.setField(fix.MsgType(fix.MsgType_NewOrderSingle)) #39 = D?


        message.setField(fix.ClOrdID(self.genExecID()))  # 11 = Unique Sequence Number

        message.setField(fix.Side(direction))  # 43 = 1 BUY
        message.setField(fix.Symbol(symbol))  # 55 = MSFT
        message.setField(fix.OrderQty(qty))  # 38 = 1000
        if _price:
            message.setField(fix.Price(_price))
        message.setField(fix.OrdType(order_type))  # 40=2 Limit Order
        message.setField(fix.HandlInst(fix.HandlInst_MANUAL_ORDER_BEST_EXECUTION))  # 21 = 3
        message.setField(fix.TimeInForce('0'))      #TEST to see what 0 is ?
        message.setField(fix.Text("NewOrderSingle"))

        trstime = fix.TransactTime()
        trstime.setString(datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3])
        message.setField(trstime)

        fix.Session.sendToTarget(message, self.sessionID)

    def run(self):
        """Run"""
        while 1:
            options = str(input("Please choose 1 for Put New Order or 2 for Exit!\n"))

            ## Limit Buy (Example)
            if options == '1':
                self.put_new_order()
                print("Done: Put New Order\n")
                continue

            ## Limit Sell (ZO)
            if options == '-1':
                self.send_order('MSFT',-1, 10000,100,'LMT')

            if  options == '2':
                sys.exit(0)

            else:
                print("Valid input is 1 for order, 2 for exit\n")
            time.sleep(2)

# Script/App to generate a payment on an Envisionware Job Queue Engine
# Requirements :
# PC that runs this App has envisionware Print Client installed, and 
# configured to print to the print server where the payment is to be 
# created.
# A virtual payment printer has been created on the Print Server.
# The folder on the print server where the jqe database resides is a
# shared folder

import wx
import wx.xrc
import logging
# import packages needed for generate_payment function
from sys import exit
import pyodbc
import datetime
import os
import subprocess

# Credentials for access to print server share
SHARE_USER = 'username'
SHARE_PW = 'password'

def configure_logger():
    logger = logging.getLogger('Eware_Payments_Generator')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('logs.txt')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%d/%m/%Y %H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# Function to take a card Number and payment amount, and generate payment
# payment entries into the JQE Database
def generate_payment(cardNo, payment_amount):
    computername = os.getenv("COMPUTERNAME")
    logger.info('PC : ' + computername)

    # Find the print server from envisionware print client config file:
    config_file = (
    	r'C:\Program Files (x86)\EnvisionWare\lptone\lptclient\config\lptclient.properties'
    	)

    # ************** TEST LPT FILE PATH ****************
    # config_file = r"lptclient.properties"
    # ***************************************************

    try:
        with open(config_file, 'r') as fb:
            for line in fb:
                if 'jqe.host' in line:
                    print_server = line.split('=')[1].rstrip()
                    
                    logger.info('print_server : ' + print_server)
    except:
        logger.debug(
            'Unable to find print client config file at ' + config_file)

    print_share = '\\\\' + print_server + '\\lptjqe'
    # ************** LIVE DB FILE PATH ******************
    db_file = r'''Q:/jqe.mdb'''
    # ***************************************************

    # ************** TEST DB FILE PATH ******************
    # db_file = r'''Q:/jqe_test.mdb'''
    # ***************************************************

    # ************** LOCAL TEST DB FILE PATH ************
    # db_file = r'''jqe_test.mdb'''
    # ***************************************************

    FNULL = open(os.devnull, 'w')
    if not os.path.isfile(db_file):
        subprocess.call(['net', 
        	'use', 
        	'Q:', 
        	print_share, 
        	'/user:' + SHARE_USER,
        	SHARE_PW], 
        	stdout=FNULL, 
        	stderr=subprocess.STDOUT)

        logger.info('Mapping network drive : ' + print_share)

    user = ''
    password = ''
    odbc_conn_str = 'DRIVER={Microsoft Access Driver (*.mdb)};DBQ=%s;UID=%s;PWD=%s' % (
        db_file, user, password)
    logger.info('Opening DB connection : ' + odbc_conn_str)
    cnxn = pyodbc.connect(odbc_conn_str)
    cursor = cnxn.cursor()

    # Get the max jobKey from the jobinformation table
    cursor.execute("SELECT MAX(jobKey) FROM jobinformation;")

    # assign it to variable
    for row in cursor:
        maxJobKey = row[0]

    # get the jobNumber corresponding to that jobKey
    cursor.execute("SELECT MAX(jobNumber) FROM jobinformation;")

    # assign it to variable
    for row in cursor:
        maxJobNo = row[0]
        # logger.info('maxJobNo : ' + maxJobNo)

    # Contruct the new table entry in jobinformation
    jobKey = maxJobKey + 1
    jobNumber = maxJobNo + 1
    jobDocumentName = "'$" + ("%.2f" % payment_amount) + " - Payment'"
    jobPrinterFamily = "'Payments'"
    jobClient = "'" + computername + "'"
    jobPatronId = "'" + cardNo + "'"
    jobPrivateJob = 0
    jobPages = 1
    jobCost = float(payment_amount) * 100
    jobGuestJob = 0
    now = datetime.datetime.today()
    jobSubmitted = "'" + now.strftime("%d/%m/%Y %X %p") + "'"
    tomorrow = now + datetime.timedelta(days=1)
    jobExpireTime = "'" + tomorrow.strftime("%d/%m/%Y %X %p") + "'"
    jobCopies = 1

    insertstring = ('INSERT INTO jobinformation (jobKey,'
    											'jobNumber,'
    											'jobDocumentName,'
    											'jobPrinterFamily,'
    											'jobClient,'
    											'jobPatronId,'
    											'jobPrivateJob,'
    											'jobPages,'
    											'jobCost,'
    											'jobGuestJob,'
    											'jobSubmitted,'
    											'jobExpireTime,'
    											'jobCopies) VALUES '
    											'(%s,%s,%s,%s,%s,%s,'
    											'%s,%s,%s,%s,%s,%s,%s);' %
    											(str(jobKey),
    											 str(jobNumber), 
    											 jobDocumentName, 
    											 jobPrinterFamily, 
    											 jobClient, 
    											 jobPatronId, 
    											 str(jobPrivateJob), 
    											 str(jobPages), 
    											 str(jobCost), 
    											 str(jobGuestJob), 
    											 jobSubmitted, 
    											 jobExpireTime, 
    											 str(jobCopies))
    											)

    logger.info('Writing to DB : ' + insertstring)

    # Insert the new data into the jobinformation table
    cursor.execute(insertstring)
    logger.info('Committing to DB')
    cnxn.commit()

    # Get the max queKey from the jobqueue table
    cursor.execute("SELECT MAX(queKey) FROM jobqueue;")

    # Assign to variable
    for row in cursor:
        maxQueKey = row[0]

    # if the que is empty, assign the queKey 1, else increment it.
    if maxQueKey is None:
        queKey = 1
    else:
        queKey = maxQueKey + 1
    # Contruct the new table entry in jobinformation

    insertstring = "INSERT INTO jobqueue (queKey,queJobInfoKey) \
    				VALUES (%s,%s);" % (str(queKey), str(jobKey))

    logger.info('Writing to database : ' + insertstring)
    cursor.execute(insertstring)
    logger.info('Committing to DB')
    cnxn.commit()

    # print('---INSERT jobqueue SQL STATEMENT---')
    # print(insertstring)
    logger.info('Closing connection to DB')
    cnxn.close()
    # os.system(r'net use p: /delete')
    logger.info('Deleting DB mapping')
    subprocess.call(['net', 'use', 'Q:', '/delete'],
                    stdout=FNULL, stderr=subprocess.STDOUT)
    logger.info('Successfully generated payment : ' +
                cardNo + ' | $' + str(payment_amount))
    Success_Popup = SuccessPopupFrame(None)
    Success_Popup.Show(True)

########################################################################
# Class StaffPaymentGenerator - Main Frame
########################################################################


class StaffPaymentGenerator (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, 
        				 parent, 
        				 id=wx.ID_ANY, 
        				 title=u"Envisionware Payment Generator", 
        				 pos=wx.DefaultPosition, 
        				 size=wx.Size(420, 490),
        				 style=wx.CAPTION 
        				 | wx.CLOSE_BOX 
        				 | wx.SYSTEM_MENU 
        				 | wx.TAB_TRAVERSAL)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetFont(wx.Font(10, 70, 90, 90, False, "Segoe UI Light"))
        self.SetBackgroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU))

        _icon = wx.Icon()
        _icon.CopyFromBitmap(wx.Bitmap("dollar_256.png", 
        								wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        bSizer4 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel1 = wx.Panel(self, 
        						wx.ID_ANY, 
        						wx.DefaultPosition, 
        						wx.DefaultSize, 
        						wx.TAB_TRAVERSAL)
        bSizer51 = wx.BoxSizer(wx.VERTICAL)

        bSizer61 = wx.BoxSizer(wx.HORIZONTAL)

        self.CardNoLabel = wx.StaticText(self.m_panel1, 
        						wx.ID_ANY, 
        						u"Card No :", 
        						wx.DefaultPosition, 
        						wx.DefaultSize, 0)
        self.CardNoLabel.Wrap(-1)
        self.CardNoLabel.SetFont(wx.Font
        						(12, 74, 90, 91, 
        							False, 
        							"Segoe UI Light"))
        
        self.CardNoLabel.SetToolTip(u'Enter a patron library card number, or a '
        							 'unique code.\nThis will be used to access'
        							 ' the payment at the Public Print Release'
        							 ' Terminal.\nIf no card number is entered,'
        							 ' a code will be automatically generated.')

        bSizer61.Add(self.CardNoLabel,
        			 0,
        			 wx.ALIGN_CENTER_VERTICAL
        			 | wx.ALL,
        			 5)

        self.CardNo = wx.TextCtrl(self.m_panel1,
        						  wx.ID_ANY,
        						  wx.EmptyString,
        						  wx.DefaultPosition,
        						  wx.Size(200, -1),
        						  0)
        self.CardNo.SetFont(wx.Font(12, 74, 90, 91, False, "Segoe UI Light"))
        self.CardNo.SetToolTip(u'Enter a patron library card number, or a '
        						'unique code.\nThis will be used to access the ' 
        						'payment at the Public Print Release Terminal.'
        						'\nIf no card number is entered, a code will ' 
        						'be automatically generated.')

        bSizer61.Add(self.CardNo, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        self.m_staticText3 = wx.StaticText(self.m_panel1,
        								   wx.ID_ANY,
        								   u"(Optional)",
        								   wx.DefaultPosition,
        								   wx.DefaultSize,
        								   0)
        self.m_staticText3.Wrap(-1)
        self.m_staticText3.SetFont(
            wx.Font(10, 74, 90, 91, False, "Segoe UI Light"))
        self.m_staticText3.SetToolTip(u'Enter a patron library card number,'
        							   'or a unique code.\nThis will be used '
        							   'to access the payment at the Public '
        							   'Print Release Terminal.\nIf no card '
        							   'number is entered, a code will be '
        							   'automatically generated.')

        bSizer61.Add(self.m_staticText3, 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        bSizer51.Add(bSizer61, 1, wx.EXPAND, 5)

        Payment_amount_boxChoices = [u"$2",
        							 u"$5",
        							 u"$6",
        							 u"$9",
        							 u"$10",
        							 u"$20"]

        self.Payment_amount_box = wx.RadioBox(self.m_panel1,
        									  wx.ID_ANY,
        									  u"Select Payment Amount",
        									  wx.DefaultPosition,
        									  wx.Size(400, -1),
        									  Payment_amount_boxChoices,
        									  1,
        									  wx.RA_SPECIFY_COLS)

        self.Payment_amount_box.SetSelection(0)
        self.Payment_amount_box.SetFont(wx.Font(12, 74, 90, 91,
        										False,
        										"Segoe UI Light"))

        bSizer51.Add(self.Payment_amount_box,
        			 0, 
        			 wx.ALL |
                     wx.ALIGN_CENTER_HORIZONTAL,
                     5)

        bSizer41 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer41.SetMinSize(wx.Size(-1, 65))
        self.Other_amount_label = wx.StaticText(self.m_panel1,
        										wx.ID_ANY,
        										u"Other\nAmount : $",
        										wx.DefaultPosition,
        										wx.DefaultSize,
        										0)

        self.Other_amount_label.Wrap(-1)
        self.Other_amount_label.SetFont(wx.Font(12, 74, 90, 91,
        										False,
        										"Segoe UI Light"))

        self.Other_amount_label.SetToolTip(u'If the payment amount is not '
        									'listed above, enter a custom '
        									'payment amount here. This amount '
        									':\n - Cannot contain any increment'
        									' of 5 cents (as the coinboxes do '
        									'not accept 5c pieces) e.g $17.05'
        									'\n - Must be less than $20 in '
        									'total\n')

        bSizer41.Add(self.Other_amount_label, 0, wx.ALL, 5)

        self.Other_Amount = wx.TextCtrl(self.m_panel1,
        								wx.ID_ANY,
        								wx.EmptyString,
        								wx.DefaultPosition,
        								wx.Size(180, -1),
        								wx.TE_PROCESS_ENTER)

        self.Other_Amount.SetFont(wx.Font(12, 74, 90, 91,
        						  False,
        						  "Segoe UI Light"))
        self.Other_Amount.SetToolTip(u'If the payment amount is not listed '
        							  'above, enter a custom payment amount '
        							  'here. This amount :\n - Cannot contain '
        							  'any increment of 5 cents (as the '
        							  'coinboxes do not accept 5c pieces) '
        							  'e.g $17.05\n - Must be less than $20 '
        							  'in total')

        bSizer41.Add(self.Other_Amount,
        			 0,
                     wx.ALIGN_CENTER_VERTICAL
                     | wx.ALL,
                     5)

        self.m_staticText31 = wx.StaticText(self.m_panel1,
        									wx.ID_ANY,
        									u"(Optional)",
        									wx.DefaultPosition,
        									wx.DefaultSize,
        									0)
        self.m_staticText31.Wrap(-1)
        self.m_staticText31.SetFont(
            wx.Font(10, 74, 90, 91, False, "Segoe UI Light"))
        self.m_staticText31.SetToolTip(u'If the payment amount is not listed '
        								'above, enter a custom payment amount '
        								'here. This amount :\n - Cannot contain'
        								' any increment of 5 cents (as the '
        								'coinboxes do not accept 5c pieces) '
        								'e.g $17.05\n - Must be less than $20 '
        								'in total')

        bSizer41.Add(self.m_staticText31, 0,
                     wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

        bSizer51.Add(bSizer41, 1, wx.EXPAND, 5)

        bSizer5 = wx.BoxSizer(wx.HORIZONTAL)

        self.submit_button = wx.Button(self.m_panel1,
        							   wx.ID_ANY,
        							   u"Submit",
        							   wx.DefaultPosition,
        							   wx.Size(150, 50),
        							   0)

        self.submit_button.SetFont(wx.Font(12, 74, 90, 91,
        								   False,
        								   "Segoe UI Light"))

        bSizer5.Add(self.submit_button, 0, wx.ALL, 5)

        self.cancel_button = wx.Button(self.m_panel1,
        							   wx.ID_ANY,
        							   u"Cancel",
        							   wx.DefaultPosition,
        							   wx.Size(150, 50),
        							   0)

        self.cancel_button.SetFont(wx.Font(12, 74, 90, 91,
        								   False,
        								   "Segoe UI Light"))

        bSizer5.Add(self.cancel_button, 0, wx.ALL, 5)

        bSizer51.Add(bSizer5, 1, wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.m_panel1.SetSizer(bSizer51)
        self.m_panel1.Layout()
        bSizer51.Fit(self.m_panel1)
        bSizer4.Add(self.m_panel1, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer4)
        self.Layout()

        self.Centre(wx.BOTH)

        # Connect Events
        self.Other_Amount.Bind(wx.EVT_TEXT_ENTER, self.submit_payment)
        self.submit_button.Bind(wx.EVT_BUTTON, self.submit_payment)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.cancel)

    def __del__(self):
        pass

    # Virtual event handlers, overide them in your derived class
    def submit_payment(self, event):
        event.Skip()

    def cancel(self, event):
        event.Skip()

########################################################################
# Class AmountErrorPopupFrame
########################################################################


class AmountErrorPopupFrame (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self,
        				  parent,
        				  id=wx.ID_ANY,
        				  title=u'Something went wrong!',
        				  pos=wx.DefaultPosition,
        				  size=wx.Size(-1, -1),
        				  style=wx.CAPTION 
        				  | wx.CLOSE_BOX 
        				  | wx.SYSTEM_MENU 
        				  | wx.TAB_TRAVERSAL
        				  )

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetForegroundColour(wx.Colour(0, 0, 0))
        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        _icon = wx.Icon()
        _icon.CopyFromBitmap(wx.Bitmap("red_X.png", 
        								wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.Popup_panel = wx.Panel(self,
        							wx.ID_ANY,
        							wx.DefaultPosition,
        							wx.DefaultSize,
        							wx.TAB_TRAVERSAL)

        bSizer2 = wx.BoxSizer(wx.VERTICAL)

        self.popup_staticText1 = wx.StaticText(self.Popup_panel,
        									   wx.ID_ANY,
        									   u"Please enter a valid amount in"
        									   " the 'Other Amount' field.\n\n"
        									   "This amount cannot contain any "
        									   "increment of 5 cents\n(as the "
        									   "coinboxes do not accept 5c "
        									   "pieces), and must be\nless than"
        									   " $20 in total.",
        									   wx.DefaultPosition,
        									   wx.DefaultSize,
        									   0)

        self.popup_staticText1.Wrap(-1)
        self.popup_staticText1.SetFont(
            wx.Font(12, 74, 90, 91, False, "Segoe UI Light"))
        bSizer2.Add(self.popup_staticText1, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.OK_button1 = wx.Button(self.Popup_panel,
        							wx.ID_ANY,
        							u"OK",
        							wx.DefaultPosition,
        							wx.DefaultSize,
        							0)

        self.OK_button1.SetFont(wx.Font(12, 74, 90, 91,
        								False,
        								"Segoe UI Light"))

        bSizer2.Add(self.OK_button1, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.Popup_panel.SetSizer(bSizer2)
        self.Popup_panel.Layout()
        bSizer2.Fit(self.Popup_panel)
        bSizer1.Add(self.Popup_panel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer1)
        self.Layout()
        bSizer1.Fit(self)

        self.Centre(wx.BOTH)

        # Connect Events
        self.OK_button1.Bind(wx.EVT_BUTTON, self.OK_button_click)

    def __del__(self):
        pass

    # Virtual event handlers, overide them in your derived class
    def OK_button_click(self, event):
        event.Skip()


class ErrorPopupFrame(AmountErrorPopupFrame):

    def __init__(self, parent):
        AmountErrorPopupFrame.__init__(self, parent)
        
    def OK_button_click(self, event):
        self.Close()

########################################################################
# Class AmountErrorPopupFrame
########################################################################


class MasterSuccessPopupFrame (wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self,
        				  parent,
        				  id=wx.ID_ANY,
        				  title=u'Success - Payment Created',
                          pos=wx.DefaultPosition,
                          size=wx.Size(-1, -1),
						  style=wx.CAPTION 
        				  | wx.CLOSE_BOX 
        				  | wx.SYSTEM_MENU 
        				  | wx.TAB_TRAVERSAL
        				  )

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetForegroundColour(wx.Colour(0, 0, 0))
        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        _icon = wx.Icon()
        _icon.CopyFromBitmap(wx.Bitmap("green_tick.png", 
        								wx.BITMAP_TYPE_ANY))
        self.SetIcon(_icon)        

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.Popup_panel = wx.Panel(self,
        							wx.ID_ANY,
        							wx.DefaultPosition,
        							wx.DefaultSize,
        							wx.TAB_TRAVERSAL)

        bSizer2 = wx.BoxSizer(wx.VERTICAL)

        self.popup_staticText1 = wx.StaticText(self.Popup_panel,
        									   wx.ID_ANY,
        									   u"A $" + 
        									   ("%.2f" % frame.payment_amount) +
        									   ' payment has been created. '
        									   'Please enter :',
        									   wx.DefaultPosition,
        									   wx.DefaultSize,
        									   0)

        self.popup_staticText1.Wrap(-1)

        self.popup_staticText1.SetFont(wx.Font(12, 74, 90, 91,
        									   False,
        									   "Segoe UI Light"))

        bSizer2.Add(self.popup_staticText1, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.m_staticText2 = wx.StaticText(self.Popup_panel,
        								   wx.ID_ANY,
        								   frame.cardNo,
        								   wx.DefaultPosition,
        								   wx.DefaultSize,
        								   0)

        self.m_staticText2.Wrap(-1)
        self.m_staticText2.SetFont(wx.Font(14, 74, 90, 92, False, "Segoe UI"))
        bSizer2.Add(self.m_staticText2, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.popup_staticText2 = wx.StaticText(self.Popup_panel,
        									   wx.ID_ANY,
        									   u'into the Public Print Release '
        									   'to access this payment.',
        									   wx.DefaultPosition,
        									   wx.DefaultSize,
        									   0)

        self.popup_staticText2.Wrap(-1)
        self.popup_staticText2.SetFont(wx.Font(12, 74, 90, 91,
        									   False,
        									   "Segoe UI Light"))

        bSizer2.Add(self.popup_staticText2, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.OK_button1 = wx.Button(self.Popup_panel,
        							wx.ID_ANY,
        							u"OK",
        							wx.DefaultPosition,
        							wx.DefaultSize,
        							0)

        self.OK_button1.SetFont(wx.Font(12, 74, 90, 91,
        								False,
        								"Segoe UI Light"))

        bSizer2.Add(self.OK_button1, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        self.Popup_panel.SetSizer(bSizer2)
        self.Popup_panel.Layout()
        bSizer2.Fit(self.Popup_panel)
        bSizer1.Add(self.Popup_panel, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer1)
        self.Layout()
        bSizer1.Fit(self)

        self.Centre(wx.BOTH)

        # Connect Events
        self.OK_button1.Bind(wx.EVT_BUTTON, self.OK_button_click)

    def __del__(self):
        pass

    # Virtual event handlers, overide them in your derived class
    def OK_button_click(self, event):
        event.Skip()


class SuccessPopupFrame(MasterSuccessPopupFrame):

    def __init__(self, parent):
        MasterSuccessPopupFrame.__init__(self, parent)

    def OK_button_click(self, event):
        self.Close()
        logger.info('Application Exiting')
        exit()

###########################################################################
# Class RunFrame - Main Application Frame
###########################################################################


class RunFrame(StaffPaymentGenerator):
    # constructor

    def __init__(self, parent):
        # initialize parent class
        StaffPaymentGenerator.__init__(self, parent)
        self.cardNo = ''
        self.payment_amount = 0.0

    def cancel(self, event):
        self.Close()
        exit()

    def submit_payment(self, event):
        self.cardNo = self.CardNo.GetValue()
        radio_amount_index = self.Payment_amount_box.GetSelection()
        radio_amount = self.Payment_amount_box.GetString(radio_amount_index)
        other_amount = self.Other_Amount.GetValue()

        # Initialize payment amount
        self.payment_amount = 0.0

        # If there is no amount entered in the 'Other Amount' field, then use
        # the selected Radio button amount
        if not other_amount:
            self.payment_amount = float(radio_amount[1:])

        # Check if anything was entered in the 'other amount' field.
        elif other_amount:
            # Check if the data entered is an int or a float (ie numerical), and
            # does not require coins smaller than 10c to pay
            try:
                # Check the amount has 2 or less decimal places (ie is not an
                # invalid amount)

                if len(str(other_amount).split('.')[1]) > 2:
                	logger.debug('Payment generation failed - other_amount '
                				 'has greater than 2 decimal places' +
                				 str(other_amount))
                	raise Exception('Amount entered is invalid')
                # Convert the data to a float
                other_amount = float(other_amount)

                # Check amount is not zero
                if other_amount <= 0:
                    logger.debug('Payment generation failed - other_amount '
                    			 '<= 0 : ' + str(other_amount))

                    raise Exception('Amount entered is zero')
                if other_amount > 20:
                    logger.debug('Payment generation failed - other_amount '
                    			 '> 20: ' + str(other_amount))

                    raise Exception('Amount entered cannot be greater than $20')



                # Check amount ends in a zero, ie does not require coins smaller
                # than 10c
                # Convert float to string with 2 dec places:
                str_other_amount = ("%.2f" % other_amount)

                # Check last character is not a zero
                if str_other_amount[-1:] != '0':
                    logger.debug('Payment generation failed - invalid amount : '
                    			 + str(other_amount))

                    raise Exception('Amount entered requires invalid coins')


                self.payment_amount = other_amount

            except:
                Error_Popup = ErrorPopupFrame(None)
                Error_Popup.Show(True)
                return

        if self.cardNo == '':
            self.cardNo = 'pay' + ("%.0f" % self.payment_amount)

        # Send details to generate_payment function
        logger.info('Generating Payment : ' + self.cardNo +
                    ' | ' + str(self.payment_amount))
        logger.debug('Calling generate_payment(' + self.cardNo +
                     ',' + str(self.payment_amount) + ')')
        generate_payment(self.cardNo, self.payment_amount)
        # print(cardNo + " : " + str(payment_amount))


logger = configure_logger()
app = wx.App(False)
frame = RunFrame(None)
frame.Show(True)
logger.info('*************** Application started ***************')
app.MainLoop()

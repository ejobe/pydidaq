import serial
import time

READ_BYTE=0x01
WRITE_BYTE=0x02
BYTES_PER_WORD = 4

#useful general purpose registers
adr_fw_version = 0x00
adr_board_version = 0x01
adr_misc_ctrl  = 0x34

class DidaqDebugSerial:
    def __init__(self, dev='/dev/ttyUSB0'):
        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.port=dev
        self.ser.open()
        self.version=[]
        self.board_id=[]
        self.BYTE_ADDRESS_BITSHIFT = 2
        
    def write(self, address_word, data_words):
        '''
        data is 4 byte list (hex)
        write_words is a list of 4-byte lists'''
        send_word = [WRITE_BYTE] + address_word + [len(data_words)]
        hex_string = bytes(send_word)
        #print('sending write to', hex_string)
        try:
            self.ser.write(hex_string)
        except Exception as e:
            print('error')
        
        for i in range(len(data_words)):
            self.ser.write(bytes(data_words[i]))

    def read(self, data, num_words):
        send_word=[READ_BYTE] + data + [num_words]
        self.ser.write(bytes(send_word))
        readback = self.ser.read(num_words * BYTES_PER_WORD)
        #print('sending', send_word, 'reading',readback, list(bytes(readback)))
        return list(bytes(readback))

    def getFwVersion(self):
        self.version = self.read([0x01,0x08,0x00,(adr_fw_version << self.BYTE_ADDRESS_BITSHIFT)], 1)
        return self.version
    
    def getBoardVersion(self):
        self.version = self.read([0x01,0x08,0x00,(adr_board_version << self.BYTE_ADDRESS_BITSHIFT)], 1)
        return self.version
    
    def enableADCPowerRegs(self, enable=True):
        header_addr=[0x01,0x08,0x00,(adr_misc_ctrl << self.BYTE_ADDRESS_BITSHIFT)]
        regval = self.read(header_addr, 1)
        print(regval)
        if enable == True:
            regval[3] = regval[3] | 0x30
            self.write(header_addr, [regval])
        else:
            regval[3] = regval[3] & ~0x30
            self.write(header_addr, [regval])
        regval=self.read(header_addr, 1)
        return regval
   
    def enableCalPulse(self, enable=True):
        header_addr=[0x01,0x08,0x00,(adr_misc_ctrl << self.BYTE_ADDRESS_BITSHIFT)]
        regval = self.read(header_addr, 1)
        print(regval)
        if enable == True:
            regval[3] = regval[3] | 0x0F
            self.write(header_addr, [regval])
        else:
            regval[3] = regval[3] & ~0x0F
            self.write(header_addr, [regval])
        regval=self.read(header_addr, 1)
        return regval

##------------------------------------------------     

class DidaqSPIHost:
    #useful spi host control registers
    map = {
        'adr_spi_core_rev' : 0x00,
        'adr_spi_setngs_0' : 0x03,
        'adr_spi_setngs_1' : 0x04,
        'adr_spi_ctrl'     : 0x05, #fifo reset
        'adr_spi_action'   : 0x07,
        'adr_spi_tx_data'  : 0x08,
        'adr_spi_rx_data'  : 0x0A}

    def __init__(self, spi_clk_divide_ctrl=4):
        ''' spi_clk_divide_ctrl; core_clk=125MHz
        0  = core_clk/2 
        1  = core_clk/4 
        2  = core_clk/6
        3  = core_clk/8     
        4  = core_clk/10
        5  = core_clk/16
        6  = core_clk/18
        7  = core_clk/20
        8  = core_clk/25
        9  = core_clk/50
        10 = core_clk/100
        11 = core_clk/200'''

        self.ser = DidaqDebugSerial()
        #set SPI bus config 0 settings (assuming detaults are all ok except for possibly the sclk rate)
        regval = self.ser.read([0x01,0x02,0x00,self.map['adr_spi_setngs_0']<<self.ser.BYTE_ADDRESS_BITSHIFT],1)
        self.ser.write([0x01,0x02,0x00,self.map['adr_spi_setngs_0']<<self.ser.BYTE_ADDRESS_BITSHIFT],
                       [[regval[0], regval[1], regval[2], ((spi_clk_divide_ctrl << 2) & 0x3C) | regval[3]]])
        self.fifoReset()

    def fifoReset(self, tx=True, rx=True):
        '''flush tx fifo, rx fifo, or both
        '''
        reset_bits = 0x00
        if tx == True:
            reset_bits = 0x01
        reset_bits = reset_bits | (rx<<1)
        self.ser.write([0x01,0x02,0x00,self.map['adr_spi_ctrl']<<self.ser.BYTE_ADDRESS_BITSHIFT],
                       [[0x00,0x00,0x00, reset_bits]])

    def spiWriteData(self, data):
        '''data-> list of bytes
        '''
        for i in range(len(data)):
            self.ser.write([0x01,0x02,0x00,self.map['adr_spi_tx_data']<<self.ser.BYTE_ADDRESS_BITSHIFT],
                           [[0x00,0x00,0x00, 0xFF & data[i]]]) 

    def spiReadData(self, num_bytes):
        read_data=[]
        for i in range(num_bytes):
            read_data.append(self.ser.read([0x01,0x02,0x00,
                                            self.map['adr_spi_rx_data']<<self.ser.BYTE_ADDRESS_BITSHIFT],1)[3])
        return read_data
        
    def spiRxFifoLevel(self):
        '''return number of bytes left in the Rx FIFO
        '''
        regval = self.ser.read([0x01,0x02,0x00,0x0B<<self.ser.BYTE_ADDRESS_BITSHIFT],1)
        return (regval[2] << 8) | regval[3]
    
    def spiTransaction(self, num_bytes_in_transaction=4):
        '''set the number of bytes and start transaction
        '''
        self.ser.write([0x01,0x02,0x00,self.map['adr_spi_action']<<self.ser.BYTE_ADDRESS_BITSHIFT],
                           [[0x00,0xFF & num_bytes_in_transaction,0x00,0x01]])

##------------------------------------------------     
        
class SDM:
    def __init__(self):
        self.ser = DidaqDebugSerial()    
        self.command_addr = [0x01, 0x0C, 0x00, (0x00 << self.ser.BYTE_ADDRESS_BITSHIFT)]
        self.command_last_word_addr = [0x01, 0x0C, 0x00, (0x01 << self.ser.BYTE_ADDRESS_BITSHIFT)]
        self.readValue(16) #flush
    def getFifoFreeSpace(self):
        header_addr = [0x01, 0x0C, 0x00, (0x02 << self.ser.BYTE_ADDRESS_BITSHIFT)]
        retval_cmd=self.ser.read(header_addr, 1)
        header_addr = [0x01, 0x0C, 0x00, (0x06 << self.ser.BYTE_ADDRESS_BITSHIFT)]
        retval_rps=self.ser.read(header_addr, 1)
        print("write fifo:",retval_cmd, "read fifo:", retval_rps)

    def readValue(self, num_words):
        header_addr = [0x01, 0x0C, 0x00, (0x05 << self.ser.BYTE_ADDRESS_BITSHIFT)]
        retval=[]
        for i in range(num_words):
            retval.append(self.ser.read(header_addr, 1))
        return retval
    def getID(self):
        command = [0x05, 0x00, 0x00,  0x10]
        print("get JTAG id..")
        self.ser.write(self.command_last_word_addr, [command])
        self.getFifoFreeSpace()
        fid=self.readValue(2)
        print("jtag id:",fid)

    def getChipID(self):
        command = [0x06, 0x00, 0x00,  0x12]
        print("get chip id..")
        self.ser.write(self.command_last_word_addr, [command])
        self.getFifoFreeSpace()
        fid=self.readValue(3)
        print("chip id:",fid)

    def reconfigure(self):
        command = [0x01, 0x00, 0x20,  0x5C]
        print('reconfigure..')
        self.ser.write(self.command_addr, [command])
        self.ser.write(self.command_addr, [[0x00, 0x78, 0x80, 0x00]]) #address [31:0]
        self.getFifoFreeSpace()
        self.ser.write(self.command_last_word_addr, [[0x00, 0x00, 0x00, 0x00]]) #address[63:32]-should be all 0's

        self.getFifoFreeSpace()
        print(self.readValue(1))
        
    def getCoreTemps(self):
        command = [0x02, 0x00, 0x10,  0x19]
        print('getting temp..')
        self.ser.write(self.command_addr, [command])
        self.ser.write(self.command_last_word_addr, [[0x00, 0x01, 0x00, 0x3C]]) 
        self.getFifoFreeSpace()
        retval = self.readValue(5)[1:4]
        temps=[]
        for i in range(len(retval)):
            val = (0xFF & retval[i][3]) | ((0xFF & retval[i][2]) << 8) | ((0xFF & retval[i][1]) << 16)
            temps.append(val * 1./256)
        return temps

    


if __name__=="__main__":
    import time

    didaq = DidaqDebugSerial()
    print('fw_version:', didaq.getFwVersion()[3])
    print('board_version:', didaq.getBoardVersion()[3])

    sdm = SDM()
    sdm.getFifoFreeSpace()
    sdm.getChipID()
    sdm.getFifoFreeSpace()
    sdm.getID()
    sdm.getFifoFreeSpace()
    time.sleep(1)
    #sdm.reconfigure()
    print(sdm.getCoreTemps())







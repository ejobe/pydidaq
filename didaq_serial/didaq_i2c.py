import didaq_serial.didaq_debug as didaq_debug
import time

#useful FPGA i2c host registers
adr_i2c_ctrl_reg = 0x01
adr_i2c_addr_reg = 0x04
adr_i2c_data_reg = 0x05
adr_i2c_stat_reg = 0x06

#PLL chip (Si5338) details
PLL_I2C_ADR      = 0x70

class DidaqI2CHost:
    def __init__(self, dev='/dev/ttyUSB0'):
        self.ser = didaq_debug.DidaqDebugSerial(dev)
        self.idle_stat = 0
        self.ack_error = 0
        self.xfer_len  = 0 #0 [=1 byte], up to 255 [256 bytes] - note fw can do up to 1024 bytes
        
    def i2c_getStat(self):
        regval=self.ser.read([0x01,0x01,0x00, adr_i2c_stat_reg << self.ser.BYTE_ADDRESS_BITSHIFT],1)
        self.idle_stat = regval[3] & 0x01
        self.ack_error = regval[3] & 0x02
        self.xfer_len  = regval[2] & 0xFF
        return regval

    def i2c_writeStat(self, start=True, reset_fifos=False):
        regval = self.i2c_getStat()
        if start == True:
            self.ser.write([0x01,0x01,0x00, adr_i2c_stat_reg << self.ser.BYTE_ADDRESS_BITSHIFT],
                           [[regval[0], regval[1], regval[2], regval[3] | 0x01]])
        elif reset_fifos == True:
            self.ser.write([0x01,0x01,0x00, adr_i2c_stat_reg << self.ser.BYTE_ADDRESS_BITSHIFT],
                           [[regval[0], regval[1], regval[2], regval[3] | 0x40]])
        else:
            None

    def i2c_read(self, adr_to_read, chip_adr):
        '''
        adr_to_read - which register to read
        chip_adr - chip i2c address 
        SINGLE BYTE READS FOR NOW'''
        ##write address to read to FPGA host, set RW bit (1 for read)
        self.ser.write([0x01, 0x01, 0x00, adr_i2c_addr_reg << self.ser.BYTE_ADDRESS_BITSHIFT],
                       [[0x00, adr_to_read & 0xFF, 0x00, 0x80 | chip_adr]])
        ##start transaction
        self.i2c_writeStat(start=True)
        ##wait for transaction to be completed
        self.i2c_getStat()
        while(self.idle_stat==1):
            self.i2c_getStat()
        ##read FIFO
        regval=self.ser.read([0x01,0x01,0x00, adr_i2c_data_reg << self.ser.BYTE_ADDRESS_BITSHIFT],1)
        return regval

    def i2c_write(self, adr_to_write, data, chip_adr):
        '''SINGLE BYTE WRITES FOR NOW'''
        ##write data value
        self.ser.write([0x01,0x01,0x00, adr_i2c_data_reg << self.ser.BYTE_ADDRESS_BITSHIFT],
                       [[0x00,0x00,0x00,0xFF & data]])
        ##write address to write + RW bit (0 for write) to FPGA host
        self.ser.write([0x01, 0x01, 0x00, adr_i2c_addr_reg << self.ser.BYTE_ADDRESS_BITSHIFT],
                       [[0x00, adr_to_write & 0xFF, 0x00, ~0x80 & chip_adr]])
        ##start transaction
        self.i2c_writeStat(start=True)
        ##wait for transaction to be completed
        self.i2c_getStat()
        while(self.idle_stat==1):
            self.i2c_getStat()
        return True

####--------------------------------

class PLLConfig:
    def __init__(self):
        self.i2c = DidaqI2CHost()
        self.i2c.i2c_write(0xFF, 0x00, PLL_I2C_ADR) #set to page 0
        self.page=0
        
    def configure(self, filename='config/Si5338-didaq-rev2-Registers.h'):    
        #
        # config procedure for Si5338. A pain in the neck!
        #
        #disable clock outputs
        self.readModifyWrite(230, 0x10, 0x10)
        #pause LOL
        self.write(241, 0x80)
        #load register config
        self.load(filename)
        #'Validate clock input status'
        val = 4
        while val & 0x4:
            val = self.read(218)
        #'Configure PLL for locking'
        self.readModifyWrite(49, 0x00, 0x80)
        #'Initiate locking of PLL'
        self.readModifyWrite(246, 0x2, 0x2)
        #'Wait a bit'
        time.sleep(0.1)
        #'Restart LOL'
        self.write(241, 0x65)
        #'Confirm PLL Lock Status'
        val = 0x11
        print('waiting on lock status....\r')
        while val & 0x11:
            val = self.read(218)
        print('done')
        #'Copy FCAL registers'
        # 237[1:0] to 47[1:0]
        val = self.read(237)
        val &= 0x3
        self.readModifyWrite(47, val, 0x3)
        # 236 to 46
        val = self.read(236)
        self.write(46, val)
        # 235 to 45
        val = self.read(235)
        self.write(45, val)
        # set 47 [7:2] to 00101b
        self.readModifyWrite(47, 0x14, 0xFC)
        # 'Set PLL to use FCAL values'
        self.readModifyWrite(49, 0x80, 0x80)
        # Not using down-spread
        # Enable outputs reg_230[4]
        self.readModifyWrite(230, 0x00, 0x10)

    def disableOutputs(self):
        self.readModifyWrite(230, 0x10, 0x10)
    
    def load(self, filename):        
        config_registers = loadRegisterFile(filename)
        for i in range(len(config_registers)):
            mask = config_registers[i][2]
            addr = config_registers[i][0]
            val  = config_registers[i][1]
            if mask == 0:
                continue
            elif mask != 0xFF:
                self.readModifyWrite(addr, val, mask)
            else:
                self.write(addr, val)      
    
    def read(self, addr):
        val = self.i2c.i2c_read(addr, PLL_I2C_ADR)[3]
        return val

    def write(self, addr, val):
        self.i2c.i2c_write(addr, val, PLL_I2C_ADR) 

    def readModifyWrite(self, addr, val, mask):
        #
        # MASK = bits to be updated
        #
        oldval = self.read(addr)
        oldval &= mask ^ 0xFF
        #make sure we write sensible values
        val = val & mask
        val |= oldval
        self.write(addr, val)   

def loadRegisterFile(filename):
    #
    # parser of the c header file from ClockBuilderPro
    #
    pll_configuration_registers = []
    with open(filename, 'r') as f:
        for line in f:
            if line[0] == '{':
                line = line.replace('{', '')
                line = line.replace('}', '')
                line = line.replace(';', ',')
                ##OK, this should give a usable per-line list now:
                tmp = line.split(',')
                ## tmp[0]=register, tmp[1]=hex value, tmp[2]=hex mask
                pll_configuration_registers.append([int(tmp[0]), int(tmp[1], 16), int(tmp[2], 16)])
    f.close()
    
    return pll_configuration_registers



if __name__=="__main__":
    pll = PLLConfig()
    pll.configure()

    

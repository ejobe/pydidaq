import didaq

##------------------------------------------------     
## control the ADC spi interfaces, via the SBC spi interface
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

        self.fpga = didaq.Didaq()
        self.spihost_addr = 0x01020000
        
        #set SPI bus config 0 settings (assuming defaults are all ok except for possibly the sclk rate)
        regval = self.fpga.systemAccessRead(self.spihost_addr |
                                            (self.map['adr_spi_setngs_0']<<self.fpga.BYTE_ADDRESS_BITSHIFT))[2:]

        self.fpga.systemAccessWrite(self.spihost_addr | (self.map['adr_spi_setngs_0']<<self.fpga.BYTE_ADDRESS_BITSHIFT),
                                    [regval[0], regval[1], regval[2], ((spi_clk_divide_ctrl << 2) & 0x3C) | regval[3]])
        self.fifoReset()

    def fifoReset(self, tx=True, rx=True):
        '''flush tx fifo, rx fifo, or both
        '''
        reset_bits = 0x00
        if tx == True:
            reset_bits = 0x01
        reset_bits = reset_bits | (rx<<1)
        self.fpga.systemAccessWrite(self.spihost_addr | (self.map['adr_spi_ctrl']<<self.fpga.BYTE_ADDRESS_BITSHIFT),
                       [0x00,0x00,0x00, reset_bits])

    def spiWriteData(self, data):
        '''data-> list of bytes
        '''
        for i in range(len(data)):
            self.fpga.systemAccessWrite(self.spihost_addr | (self.map['adr_spi_tx_data']<<self.fpga.BYTE_ADDRESS_BITSHIFT),
                           [0x00,0x00,0x00, 0xFF & data[i]]) 

    def spiReadData(self, num_bytes):
        read_data=[]
        for i in range(num_bytes):
            rd_val = self.fpga.systemAccessRead(self.spihost_addr |   
                                                (self.map['adr_spi_rx_data']<<self.fpga.BYTE_ADDRESS_BITSHIFT))
            read_data.append(rd_val[5])
            
        return read_data
        
    def spiRxFifoLevel(self):
        '''return number of bytes left in the Rx FIFO
        '''
        regval = self.fpga.systemAccessRead(self.spihost_addr | (0x0B<<self.fpga.BYTE_ADDRESS_BITSHIFT))[2:]
        return (regval[2] << 8) | regval[3]
    
    def spiTransaction(self, num_bytes_in_transaction=4):
        '''set the number of bytes and start transaction
        '''
        self.fpga.systemAccessWrite(self.spihost_addr | (self.map['adr_spi_action']<<self.fpga.BYTE_ADDRESS_BITSHIFT),
                           [0x00,0xFF & num_bytes_in_transaction,0x00,0x01])









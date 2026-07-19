import didaq_serial.didaq_debug as didaq_debug
import didaq_serial.didaq_adc_config as didaq_adc_config
import time
import numpy

'''Handle simple didaq data acquisition
    --> Board should be configured (clocks, adcs, etc) prior
'''

class didaqJESD:
    def __init__(self):
        self.fpga = didaq_debug.DidaqDebugSerial()
        self.adc  = didaq_adc_config.ADCconfig()

    def jesdRxEn(self, en=True):
        header_addr=[0x01,0x08,0x00,(0x10 << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        if en==True:
            self.fpga.write(header_addr, [[0x00,0x00,0x1F, 0xFF]])
        else:
            self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]])

        #print(self.fpga.read(header_addr, 1))

    def jesdStatus(self):
        header_addr=[0x01,0x08,0x00,(0x13 << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        regval=self.fpga.read(header_addr, 1)
        return regval
    

    def jesdCoreRegisterRead(self, core=0):
        ''' sides: 0,1, links 0-5
        '''
        #loop thru links:
        data=[]
        for i in range(0, 253, 4):
            for j in range(6):
                header_addr=[0x01,0x08,0x00,0x12 << self.fpga.BYTE_ADDRESS_BITSHIFT] #address avs_sel_reg
                self.fpga.write(header_addr, [[0x00,0x00,0x00, j & 0xFF]]) #assign selected link 
                #check:
                #print(self.fpga.read(header_addr,1)) #check that register updated
            
                shifted_address_low = (i << 2) & 0x00FF
                shifted_address_high = ((i << 2) & 0xFF00) >> 8
                header_addr=[0x01,0x0A,shifted_address_high,shifted_address_low] #low side, jesd avs register space
                print(i, j,header_addr[2],header_addr[3],self.fpga.read(header_addr,1)) 
                regval = self.fpga.read(header_addr,1)
                _data = numpy.array([i, j,header_addr[2],header_addr[3],regval[3], regval[2], regval[1], regval[0]], dtype=numpy.int)
                data.append(_data)
                #header_addr=[0x01,0x0B,0x01,0x80] #high-side, jesd avs register space
                #print(j,header_addr,self.fpga.read(header_addr,1))
        numpy.savetxt('test_rx_jesd_regs.txt', numpy.array(data, dtype=numpy.int), fmt='%d')


    def resetAcq(self, run_reset=False):
        header_addr=[0x01,0x08,0x00,(0x0E << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #set to 0
        if run_reset == True:
            self.fpga.write(header_addr, [[0x00,0x01,0x01, 0x00]]) #flag reset bits
        else:
            self.fpga.write(header_addr, [[0x00,0x00,0x01, 0x00]]) #flag event reset bit only
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #set to 0

    def softTrig(self):
        header_addr=[0x01,0x08,0x00,(0x0E << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #set to 0
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x01]]) 
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #not self-clearing

    def acqStatus(self):
        header_addr=[0x01,0x08,0x00,(0x0F << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        regval=self.fpga.read(header_addr, 1)
        return regval
    
    def getMetaData(self):
        regval=self.fpga.read([0x01,0x08,0x00, 0x00], 1)
        print('fw ver: ',regval)

        for i in range(8):
            offset_addr = (0x0052 + i) << self.fpga.BYTE_ADDRESS_BITSHIFT
            header_addr = [0x01,0x08,(0xFF00 & offset_addr) >> 8, 0x00FF & offset_addr]
            regval=self.fpga.read(header_addr, 1)
            print(header_addr, regval)

    def ramRead(self, channel):
        header_addr = [0x01,0x08,0x00,(0x14 + channel) << self.fpga.BYTE_ADDRESS_BITSHIFT]
        print(header_addr)
        data=[]
        for i in range(512):
            _data = self.fpga.read(header_addr, 1)
            data.extend(_data)
        return(data)
    

if __name__=='__main__':
    #import matplotlib.pyplot as plt
    import didaq_rf_trig as trigger

    acq = didaqJESD()
    acq.fpga.enableCalPulse(True)

    print('jesd status',acq.jesdStatus())
    
    acq.resetAcq(True)
    acq.softTrig()
    print(acq.acqStatus())
    acq.getMetaData()
    #acq.resetAcq()

    #fig, ax = plt.subplots(10, sharex=True)
    all_data=[]
    for i in range(24):
        data=acq.ramRead(i)
        all_data.append(data)
        #ax[i].plot(numpy.array(data) , 'o-', color='black')
        #ax[i].set_ylabel('adu')
        #ax[i].set_ylim([100, 150])
        
    numpy.savetxt('test.txt', numpy.array(all_data))	
    #acq.jesdRxEn(False)
    acq.fpga.enableCalPulse(False)
    acq.resetAcq()

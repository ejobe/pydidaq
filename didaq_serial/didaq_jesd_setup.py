import didaq_debug
import didaq_adc_config
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


    def fifoFlush(self):
        header_addr=[0x01,0x08,0x00,(0x0E << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #set to 0
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x02]]) #flush
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]]) #not self-clearing

    def fifoCapture(self, startstop=0):
        header_addr=[0x01,0x08,0x00,(0x0E << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        if startstop == 0: #stop
            self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x00]])
        else: #start
            self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x01]])

    def fifoStatus(self):
        header_addr=[0x01,0x08,0x00,(0x0F << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        regval=self.fpga.read(header_addr, 1)
        return regval

    def fifoRead(self, channel):
        header_addr = [0x01,0x08,0x00,(0x14 + channel) << self.fpga.BYTE_ADDRESS_BITSHIFT]
        print(header_addr)
        data=[]
        for i in range(255):
            _data = self.fpga.read(header_addr, 1)
            data.extend(_data)
        return(data)
    

if __name__=='__main__':
    import matplotlib.pyplot as plt

    acq = didaqData()
    acq.jesdRxEn(False)
    acq.fpga.enableCalPulse(True)

    while(True):
        time.sleep(5)
        acq.fifoFlush()

        acq.jesdRxEn(True)
        time.sleep(1)
        #acq.jesdCoreRegisterRead()
        time.sleep(1)
        print('jesd status',acq.jesdStatus())
        #for i in range(6):
        #    acq.adc.adcSpiBusSel(i)
        #    acq.adc.getJesdStatus()
        #print(acq.adc.jesd_stat)
        #print(acq.jesdStatus())
        acq.fifoFlush()
        acq.fifoFlush()
        acq.fifoFlush()

        acq.fifoCapture(0)
        print('fifo',acq.fifoStatus())
        acq.fifoCapture(1)
        time.sleep(0.5)
        acq.fifoCapture(0)

        print('fifo',acq.fifoStatus())
        fig, ax = plt.subplots(24, sharex=True)
        all_data=[]
        for i in range(24):
            data=acq.fifoRead(i)
            all_data.append(data)
            ax[i].plot(numpy.array(data) , 'o-', color='black')
            ax[i].set_ylabel('adu')

        ax[-1].set_xlabel('sample')
        plt.show()

        numpy.savetxt('data.txt', numpy.array(all_data))
        time.sleep(5)

        #acq.jesdRxEn(False)
        #acq.jesdCoreRegisterRead()

import didaq
#import didaq_adc_config
import time
import numpy

'''Handle simple didaq data acquisition
    --> Board should be configured (clocks, adcs, etc) prior
'''

class didaqJESD:
    def __init__(self):
        self.fpga = didaq.Didaq()

    def jesdRxEn(self, en=True):
        header_addr=0x0010
        if en==True:
            self.fpga.write(header_addr, [0x00,0x00,0x1F, 0xFF])
        else:
            self.fpga.write(header_addr, [0x00,0x00,0x00, 0x00])

        #print(self.fpga.read(header_addr, 1))

    def jesdStatus(self):
        regval=self.fpga.read(address=0x0013)
        return regval
    
    def resetAcq(self, run_reset=False):
        header_addr= 0x000E
        self.fpga.write(header_addr, [0x00,0x00,0x00, 0x00]) #set to 0
        if run_reset == True:
            self.fpga.write(header_addr, [0x00,0x01,0x00, 0x00]) #flag reset bits
        else:
            self.fpga.write(header_addr, [0x00,0x00,0x01, 0x00]) #flag event reset bit only
        self.fpga.write(header_addr, [0x00,0x00,0x00, 0x00]) #set to 0

    def softTrig(self):
        header_addr=0x000E
        self.fpga.write(header_addr, [0x00,0x00,0x00, 0x00])
        self.fpga.write(header_addr, [0x00,0x00,0x00, 0x01]) 
        self.fpga.write(header_addr, [0x00,0x00,0x00, 0x00]) 
        
    def acqStatus(self):
        header_addr=0x000F
        regval=self.fpga.read(header_addr)
        return regval
    
    def getMetaData(self, verbose=False):
        regval=self.fpga.read(0x0000)
        if verbose:
            print('fw ver: ',regval)

        for i in range(8):
            offset_addr = (0x0052 + i)
            header_addr = offset_addr
            regval=self.fpga.read(header_addr)
            if verbose:
                print(hex(header_addr), regval)

    def ramRead(self, channel):
        header_addr = 0x0014 + channel
        data=[]
        for i in range(512):
            _data = self.fpga.read(header_addr)
            data.extend(_data)
        #print(hex(header_addr), hex(data[20]))
        return(data)

def takeEvent(cal_pulse=False, filename='test.txt'):
    acq=didaqJESD()
    acq.fpga.enableCalPulse(cal_pulse)

    print('jesd status',acq.jesdStatus())
    
    acq.resetAcq(True)
    time.sleep(0.1)
    acq.softTrig()
    print('acq status',acq.acqStatus())
    acq.getMetaData()
    print('acq status',acq.acqStatus())

    all_data=[]
    for i in range(24):
        data=acq.ramRead(i)
        all_data.append(data)
    
    numpy.savetxt(filename, numpy.array(all_data))
    acq.fpga.enableCalPulse(False)
    acq.resetAcq()

    return numpy.array(all_data)

if __name__=='__main__':
    
    takeEvent(True)

    

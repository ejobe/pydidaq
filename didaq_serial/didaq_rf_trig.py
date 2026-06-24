import didaq_debug
import time

class Trig:
    reg_map = {
        'adr_coinc_1'    : 0x38,
        'adr_coinc_2'    : 0x39,
        'adr_coinc_thresh_base' : 0x3A,
        'adr_phased'     : 0x46,
	'adr_phased_thresh_base' : 0x47,
        'adr_scaler_read': 0x5C,
        'adr_scaler_sel' : 0x5D}

    def __init__(self):
        self.fpga = didaq_debug.DidaqDebugSerial()

    def setCoinc(self, module=0, enable=1, window=6,mask=0xFFF, num_coinc=2):
        if module == 0:
            addr = self.reg_map['adr_coinc_1']
        elif module == 1:
            addr = self.reg_map['adr_coinc_2']
        else:
            print('not valid module')
            return 1

        offset_addr = addr << self.fpga.BYTE_ADDRESS_BITSHIFT
        header_addr = [0x01,0x08,(0xFF00 & offset_addr) >> 8, 0x00FF & offset_addr]

        _mask = mask & 0xFFF
        _num_coinc = num_coinc & 0x7
        _enable = ((enable & 0x1) << 1) | (enable & 0x1)
        _window = window & 0xF

        self.fpga.write(header_addr, [[(0xF00 & _mask) >> 8, (0xFF & _mask), _window, (_num_coinc << 2) | _enable]])

        print(self.fpga.read(header_addr, 1))

    def setCoincThresholds(self, value=50):
        base_addr =  self.reg_map['adr_coinc_thresh_base']

        for i in range(12):
            offset_addr = (base_addr + i) << self.fpga.BYTE_ADDRESS_BITSHIFT
            header_addr = [0x01,0x08,(0xFF00 & offset_addr) >> 8, 0x00FF & offset_addr]
            self.fpga.write(header_addr, [[0x00, 0xFF & value, 0x00, 0xFF & value]])
    
    def setBeamformer(self, enable=1, mask=0xFFF, gain_sel=1, window=0):
    	addr = self.reg_map['adr_phased']
    	offset_addr = addr << self.fpga.BYTE_ADDRESS_BITSHIFT
    	header_addr = [0x01, 0x08, (0xFF00 & offset_addr) >> 8, 0x00FF & offset_addr]
	
    	_mask = mask & 0xFFF
    	_enable = ((window & 0x1) << 4) | ((enable & 0x1) << 1) | (enable & 0x1)

    	self.fpga.write(header_addr, [[(0xF00 & _mask) >> 8, (0xFF & _mask), gain_sel & 0x01, _enable]])

    	print(self.fpga.read(header_addr, 1))

    def setBeamThresholds(self, value):
    	base_addr = self.reg_map['adr_phased_thresh_base']
	
    	for i in range(10):
    	    print(i + base_addr)
    	    offset_addr = (base_addr + i) << self.fpga.BYTE_ADDRESS_BITSHIFT
    	    header_addr = [0x01, 0x08, (0xFF00 & offset_addr) >> 8, 0x00FF & offset_addr]
    	    self.fpga.write(header_addr, [[(0xFF00 & value) >> 8, 0x00FF & value, (0xFF00 & value) >> 8, 0x00FF & value]])

    def readScalers(self, verbose=True):
        sel_offset_addr =  self.reg_map['adr_scaler_sel'] << self.fpga.BYTE_ADDRESS_BITSHIFT
        rd_offset_addr = self.reg_map['adr_scaler_read'] << self.fpga.BYTE_ADDRESS_BITSHIFT
        
        sel_header_addr = [0x01,0x08,(0xFF00 & sel_offset_addr) >> 8, 0x00FF & sel_offset_addr]
        rd_header_addr = [0x01,0x08,(0xFF00 & rd_offset_addr) >> 8, 0x00FF & rd_offset_addr]
            
        self.fpga.write(sel_header_addr, [[0x00, 0x01, 0x00, 0x00]]) #latch scalers
        self.fpga.write(sel_header_addr, [[0x00, 0x00, 0x00, 0x00]]) #latch scalers
        scaler_array=[]	

        for i in range(48):
            self.fpga.write(sel_header_addr, [[0x00, 0x00, 0x00, 0xFF & i]]) #select
            scaler = self.fpga.read(rd_header_addr, 1)
            scaler_array.append(scaler)
            if verbose:
                print(i,scaler)

        return scaler_array
    	   

if __name__=='__main__':
    trig = Trig()
    trig.setCoinc(0, enable=0)
    trig.setCoincThresholds()

    trig.setBeamThresholds(2150)
    trig.setBeamformer(enable=1, window=0)
 
    trig.readScalers()

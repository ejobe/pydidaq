import didaq_debug
import didaq_data
import time

class ADCconfig:
    #useful adc09qj1300 config registers [two bytes]
    #r/w sdi data, 24bit transaction:
    #    [r/~w bit] + [15 bit address] + [8 bit data]
    #     note that data field is ignored on a read
    adc09_reg_map = {
        'adr_cpll_reset'   : 0x005C,
        'adr_cpll_fbdiv1'  : 0x003D, #P, V_DIV
        'adr_cpll_fbdiv2'  : 0x003E, #N_DIV
        'adr_vco_cal_ctrl' : 0x005D, #fifo reset
        'adr_vco_cal_stat' : 0x005E,
        'adr_jesd_stat'    : 0x0208,
        'adr_config_a'     : 0x0000,  #soft_reset
        'adr_vendor_id'    : 0x000C,
        'adr_fsrange'      : 0x0030, #fs range for all channels
        'adr_alarmstat'    : 0x02C1,
        'adr_initstat'     : 0x0270}
    
    # adc config/control registers on the FPGA fw
    #   [parallel/gpio control to ADC09xx pin]
    adc_fw_ctrl_reg_map = {
        'adr_adc_pllen'  : 0x33,
        'adr_adc_calstat': 0x32,
        'adr_adc_syncse' : 0x31,
        'adr_adc_caltrig': 0x30,
        'adr_adc_spisel' : 0x0D,
        'adr_adc_pdwn'   : 0x0C}
    
    def __init__(self):
        #instance to host the ADC config SPI bus
        self.spi = didaq_debug.DidaqSPIHost()
        #instance to host the gpio config of ADCs
        self.fpga = didaq_debug.DidaqDebugSerial()
        self.num_adcs = 6
        self.cur_adc = 0 #index current adc on spi bus
        ###alarm status dicts
        self.alarms = []
        for i in range(self.num_adcs):
            self.alarms.append({ 'fifo' : 0,
                                 'spll' : 0,
                                 'link' : 0,
                                 'realigned' : 0,
                                 'clk'  : 0})
        ###jesd status dicts
        self.jesd_stat = []
        for i in range(self.num_adcs):
            self.jesd_stat.append({ 'link'      : 0,
                                    'sync'      : 0,
                                    'aligned'   : 0,
                                    'realigned' : 0,
                                    'splllock'  : 0,
                                    'cplllock'  : 0})
    def readReg(self, adr, transaction_bytes=3):
        '''
        '''
        self.spi.fifoReset()
        self.spi.spiWriteData([0x80 | ((0x3F00 & adr) >> 8), adr & 0xFF, 0x00])
        self.spi.spiTransaction(transaction_bytes)
        rx_fifo_bytes = self.spi.spiRxFifoLevel()
        while(rx_fifo_bytes > 1): #just read the last byte
            rx_fifo_bytes = self.spi.spiRxFifoLevel()
            self.spi.spiReadData(1)
        read_byte = self.spi.spiReadData(1)
        return read_byte

    def writeReg(self, adr, data):
        self.spi.fifoReset()
        self.spi.spiWriteData([0x7F & ((0x3F00 & adr) >> 8), adr & 0xFF, data & 0xFF])
        self.spi.spiTransaction(3)

    def getVendorId(self):
        '''returns lower byte of vendor ID [0x51], just a test function
        '''
        vendor_id = self.readReg(self.adc09_reg_map['adr_vendor_id'])
        return vendor_id

    def adcSpiBusSel(self, bus):
        '''current version, each ADC is config'ed sequentially thru its spi bus
             default/reset value is 0x00 - ADC_0
        '''
        header_addr=[0x01,0x08,0x00,(self.adc_fw_ctrl_reg_map['adr_adc_spisel'] 
                                     << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0xFF & bus]])
        self.cur_adc = bus

    def adcPllEn(self, pll_en_mask):
        ''' set PLL_en gpio to high to use internal PLL
              control left/right ADC banks separately: 
               if ADC bank is off, probably best to keep this low
        '''
        header_addr=[0x01,0x08,0x00,(self.adc_fw_ctrl_reg_map['adr_adc_pllen'] 
                                     << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        self.fpga.write(header_addr, [[0x00,0x00,0x00, 0x3 & pll_en_mask]])
    
    def adcPd(self, pd_mask):
        ''' adc powerdown control
        '''
        header_addr=[0x01,0x08,0x00,(self.adc_fw_ctrl_reg_map['adr_adc_pdwn']
                                     << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        regval = self.fpga.read(header_addr, 1)
        regval[3] = 0x3F & pd_mask
        self.fpga.write(header_addr, [regval])

    def adcSyncSE(self, level=0):
        ''' adc sync control - eventually will be controlled by fw jesd rx
        '''
        header_addr=[0x01,0x08,0x00,(self.adc_fw_ctrl_reg_map['adr_adc_syncse']
                                     << self.fpga.BYTE_ADDRESS_BITSHIFT)]
        regval = self.fpga.read(header_addr, 1)
        regval[3] = 0x03 & (level << 1 | level)
        self.fpga.write(header_addr, [regval])

    def foregroundCalibration(self):
        self.writeReg(0x006C, 0x00) #write a 0
        self.writeReg(0x006C, 0x01) #set back to 1, triggers cal
        _incr=0
        _fg_cal_done = self.readReg(0x6A)[0] & 0x1
        while(_fg_cal_done != 1):
            _fg_cal_done = self.readReg(0x6A)[0] & 0x1
            _incr = _incr + 1
            if _incr > 100:
                'foreground cal failed'
                break

        return _fg_cal_done

    def adcVertRangeSetting(self, range_setting=0xA000):
        self.writeReg(0x0030, range_setting & 0xFF00 >> 8) #write a 0
        self.writeReg(0x0031, range_setting & 0x00FF)

        
    def adcPowerDownState(self):
        self.adcPllEn(0x0)
        self.fpga.enableADCPowerRegs(False)
        self.adcPd(0x00)
        self.adcSyncSE(0) 

    def adcAlarms(self, clear=False):
        ''' clear or read Alarm Status register
        '''
        if clear==True:
            self.writeReg(self.adc09_reg_map['adr_alarmstat'], 0x3F)
        
        regval = self.readReg(self.adc09_reg_map['adr_alarmstat'])[0]
        return regval

    def getJesdStatus(self, clear=False):
        ''' read JESD stat register
        '''        
        if clear==True:
            self.writeReg(self.adc09_reg_map['adr_jesd_stat'], 0x00)

        regval = self.readReg(self.adc09_reg_map['adr_jesd_stat'])[0]
        self.jesd_stat[self.cur_adc]['link'] = (regval & 0x40) >> 6
        self.jesd_stat[self.cur_adc]['sync'] = (regval & 0x20) >> 5
        self.jesd_stat[self.cur_adc]['realigned'] = (regval & 0x10) >> 4
        self.jesd_stat[self.cur_adc]['aligned'] = (regval & 0x08) >> 3
        self.jesd_stat[self.cur_adc]['splllock'] = (regval & 0x04) >> 2
        self.jesd_stat[self.cur_adc]['cplllock'] = (regval & 0x01)

    def sysRef(self, enable=True):
        '''write to clk_ctrl0 register to setup sysref receiver on the adc device
        '''
        if enable == True:
            self.writeReg(0x0029, 0xE0)
        else:
            self.writeReg(0x0029, 0x80) #default reg value

    def modeJTest(self, mode):
        '''test mode on jesd lanes. 0=normal operation
        '''
        #set jesd_en to 0
        self.writeReg(0x0200, 0x00)
        self.writeReg(0x0205, 0x1F & mode)
        self.writeReg(0x0200, 0x01)

    def configureADC(self, pd_mask, low_power_mode=True, sampling_rate=1, pll_en=False):
        '''following procedure in section 7.2.2 in datasheet, for didaq application
        '''
        #turn off adc_regulator rails
        self.adcPowerDownState()
        time.sleep(2) #let settle in case they were already on
        #set PLL enable, note that PLLREF_SE is pulled to gnd on board
        self.adcPllEn(0x3)
        if pll_en == False: #debug only 
            self.adcPllEn(0x0)
        #power on rails, while keeping PD low for ADCs to be configured
        self.adcPd(pd_mask)
        self.fpga.enableADCPowerRegs(True)
        #configure clk [try to configure clock before this and see if it works 
        #   otherwise, insert pll_config instance
        
        #self.adcSyncSE(1) 

        #now loop through ADC devices to configure C-PLL
        for i in range(self.num_adcs):
            self.adcSpiBusSel(i)
            #reset device using soft reset
            self.writeReg(self.adc09_reg_map['adr_config_a'], 0x80)
            #confirm init_done bit goes hi
            _init_done = self.readReg(self.adc09_reg_map['adr_initstat'])[0]
            while(_init_done != 1):
                #add a timeout here
                _init_done = self.readReg(self.adc09_reg_map['adr_initstat'])[0]
         
	       
            self.adcVertRangeSetting(0xFFFF)

            ####progam c-pll
            #reset c-pll
            self.writeReg(self.adc09_reg_map['adr_cpll_reset'], 0x01)
            #set vco_bias
            self.writeReg(0x3F, 0x4A)
            if sampling_rate == 1.0:
                #set P_DIV (2), V_DIV (4), and N_DIV (10)
                self.writeReg(self.adc09_reg_map['adr_cpll_fbdiv1'], 0x05)
                self.writeReg(self.adc09_reg_map['adr_cpll_fbdiv2'], 0x0A)
            elif sampling_rate == 0.5:
                #set P_DIV (4), V_DIV (4), and N_DIV (5)
                self.writeReg(self.adc09_reg_map['adr_cpll_fbdiv1'], 0x09)
                self.writeReg(self.adc09_reg_map['adr_cpll_fbdiv2'], 0x05)
            else:
                print('no sampling rate set..')
            #set vco_cal_en to enable vco trim cal
            self.writeReg(self.adc09_reg_map['adr_vco_cal_ctrl'],0x41) 
            #de-assert reset to start vco calibration and enable c-pll
            self.writeReg(self.adc09_reg_map['adr_cpll_reset'], 0x00)
            #set jesd_en to 0
            self.writeReg(0x0200, 0x00)
            #set cal en to 0
            self.writeReg(0x0061, 0x00)
            #set to low-power mode
            if low_power_mode == True:
                self.writeReg(0x0037, 0x46) #LOW_POWER1
                self.writeReg(0x029A, 0x06) #LOW_POWER2
                self.writeReg(0x029B, 0x00) #LOW_POWER3
                self.writeReg(0x029C, 0x14) #LOW_POWER4
            #set the JMODE=2 (4-lanes, quad-mode @ 8bit w/ 8B/10B encoding)
            self.writeReg(0x0201, 0x02) 
            #set the K-1 jesd value
            self.writeReg(0x0202, 0x1F) 
            #set sync_sel source, default value should be fine
            ##self.writeReg(0x0204, 0x03)
            #set calibration settings
            ##default foreground calibration settings seem fine
            #enable trig_out clock for FPGA data capture
            #----self.writeReg(0x0057, 0x82) #trig_out EN, RX_DIV=64
            #go back and check that vco cal is done
            _cpll_cal_done = self.readReg(self.adc09_reg_map['adr_vco_cal_stat'])[0] & 0x1
            _cpll_locked   = self.readReg(self.adc09_reg_map['adr_jesd_stat'])[0] & 0x1
            if _cpll_cal_done == 0 or _cpll_locked == 0:
                print('no c-pll lock for ADC ', i)

            #set to offset binary
            self.writeReg(0x0204, 0x01) 

        #another device loop for re-starting jesd links
        for i in range(self.num_adcs):
            self.adcSpiBusSel(i)
            #set cal en to 1
            self.writeReg(0x0061, 0x01)
            #set jesd_en to 1
            self.writeReg(0x0200, 0x01)
            _spll_locked = self.readReg(self.adc09_reg_map['adr_jesd_stat'])[0] & 0x4
            #foreground calibration on startup
            self.foregroundCalibration()
        
        for i in range(self.num_adcs):
            self.adcSpiBusSel(i)
            #self.sysRef(True)
            self.getJesdStatus()
            self.adcAlarms(True)       

        print(self.jesd_stat)

def run():
    jesd = didaq_data.didaqJESD()		
    jesd.jesdRxEn(False)
    time.sleep(1)
    print('configuring ADCs..')
 
    adc_config=ADCconfig()
    adc_config.configureADC(0x00, sampling_rate=1.0, pll_en=True)

    print('locking JESD links..')
    print('jesd status: ', jesd.jesdStatus())
    jesd.jesdRxEn(True)
    time.sleep(2)
    print('jesd status ([0,255,255,255] is good) :: ', jesd.jesdStatus())

    for i in range(6):
        adc_config.adcSpiBusSel(i)
        adc_config.sysRef(True)

    print('enabling sysref..done')
    
if __name__=='__main__':

    run()
    

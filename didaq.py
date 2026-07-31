#import serial
import time
import spidev
import json
import fcntl

READ_BYTE=0x01
WRITE_BYTE=0x02
BYTES_PER_WORD=4

#useful general purpose registers
adr_fw_version = 0x00
adr_board_version = 0x01
adr_misc_ctrl  = 0x34

class Didaq:
    def __init__(self, dev='/dev/spidev1.0'):
        self.spi = spidev.SpiDev()
        self.spi.open_path(dev)

        # grab file lock on spi fd
        while True:
            try:
                fcntl.flock(self.spi.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                print ('spi file lock is being held. Trying again in 3 seconds')
                time.sleep(3)

        self.spi.max_speed_hz = 5000000
        self.spi.mode = 0b01
        self.BYTE_ADDRESS_BITSHIFT=2 ##for system memory map access

    def __del__(self):
        self.spi.close()  # this should clear the filelock


    def spiXfer(self, rw, address_word, data_word):
        '''
        data is 4 byte list (hex)
        write_words is  4-byte list'''
        send_bytes= [(rw << 7) | ((address_word & 0x7F00) >> 8), address_word & 0x00FF, data_word[0], data_word[1], data_word[2], data_word[3]]
        #print(send_bytes)
        retval=self.spi.xfer2(send_bytes)
        return retval

    def write(self, address, data):
        if len(data) != 4:
            print('spi write failed, data word needs to be list of 4 bytes')
            return 1
        #print('write', hex(address))
        self.spiXfer(rw=0, address_word=address, data_word=data)

    def read(self, address):
        #print('read', hex(address))
        retval=self.spiXfer(rw=1, address_word=address, data_word=[0x00,0x00,0x00,0x00])
        return retval

    def getFwVersion(self):
        self.version = self.read(address=0x0000)[2:]
        return self.version
    
    def getBoardVersion(self):
        self.version = self.read(address=0x0001)[2:]
        return self.version
    
    def enableADCPowerRegs(self, enable=True):
        addr = 0x0034
        regval = self.read(addr)[2:]
        print(regval)
        if enable == True:
            regval[3] = regval[3] | 0x30
            self.write(addr, regval)
        else:
            regval[3] = regval[3] & ~0x30
            self.write(addr, regval)
        regval=self.read(addr)
        return regval
   
    def enableCalPulse(self, enable=True):
        addr = 0x0034
        regval = self.read(addr)[2:]
        print('misc register',regval)
        if enable == True:
            regval[3] = regval[3] | 0x0F
            self.write(addr, regval)
        else:
            regval[3] = regval[3] & ~0x0F
            self.write(addr, regval)
        regval=self.read(addr)
        return regval

    def systemAccessRead(self, address):
        '''32-bit memory-map address
        '''
        self.write(address=0x0006, data=[(address & 0xFF000000) >> 24,(address & 0x00FF0000)>>16,(address & 0x0000FF00) >> 8, address & 0x000000FF])
        self.write(address=0x0009, data=[0x00,0x00,0x00,0x01]) #read rqst
        retval = self.read(address=0x0008)
        return retval

    def systemAccessWrite(self, address, data):
        '''memory-mapped write, 32 bit address + 32 bit data
        '''
        self.write(address=0x0006, data=[(address & 0xFF000000) >> 24,(address & 0x00FF0000)>>16,(address & 0x0000FF00) >> 8, address & 0x000000FF])
        self.write(address=0x0007, data=data)
        self.write(address=0x0009, data=[0x00,0x00,0x00,0x02]) #write rqst
        

##------------------------------------------------     
# class to interface to the secure device manager on the Agilex FPGA
# via the memory-mapped interface over SPI
class SDM_SPI:
    def __init__(self):
        self.spi = Didaq()
        self.base_addr = 0x010C0000 #Mailbox client IP memory-mapped based address
        self.command_addr = self.base_addr | 0x0
        self.command_last_word_addr = self.base_addr | 0x4 #byte address
        self.CPB0_offset_addr = [0x00,0x78,0x00,0x00]
        self.CPB1_offset_addr = [0x00,0x78,0x80,0x00]
        self.FIFO_LENGTH = 256
        self.readValue(16) #flush
            
    def getFifoFreeSpace(self):
        header_addr = self.base_addr | (0x02 << self.spi.BYTE_ADDRESS_BITSHIFT)
        retval_cmd=self.spi.systemAccessRead(header_addr)
        header_addr = self.base_addr | (0x06 << self.spi.BYTE_ADDRESS_BITSHIFT)
        retval_rps=self.spi.systemAccessRead(header_addr)
        #print("write fifo:",retval_cmd, "read fifo:", retval_rps)

    def readValue(self, num_words):
        header_addr = self.base_addr | (0x05 << self.spi.BYTE_ADDRESS_BITSHIFT)
        retval=[]  
        for i in range(num_words):
            time.sleep(0.005) #this is stupid but needed, probably can check that the write/rd request system register is cleared
            retval.append(self.spi.systemAccessRead(header_addr))
        
        return retval

    def getErrorCode(self, response_header):
        #eventually enumerate the potential errors...
        if response_header[-1] != 0x00:
            return 1
        else:
            return 0
        
    def getID(self):
        command = [0x05, 0x00, 0x00,  0x10]
        print("get JTAG id..")
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.getFifoFreeSpace()
        fid=self.readValue(2)
        jtag_id = convertListToWord(fid[1])
        return jtag_id

    def getChipID(self):
        command = [0x06, 0x00, 0x00,  0x12]
        print("get chip id..")
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.getFifoFreeSpace()
        fid=self.readValue(3)
        _chip_id_hi = convertListToWord(fid[1])
        _chip_id_lo = convertListToWord(fid[2])
        chip_id = (_chip_id_hi << 32) | _chip_id_lo
        return chip_id

    def qspiOpen(self):
        command = [0x08,0x00,0x00,0x32]
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.readValue(1) #flush header response
        
    def qspiClose(self):
        command = [0x09,0x00,0x00,0x33]
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.readValue(1) #flush header response

    def qspiChipSelect(self):
        #QSPI attached to nCSO[0]
        #########
        command = [0x0A,0x00,0x10,0x34]
        self.spi.systemAccessWrite(self.command_addr, command)
        self.spi.systemAccessWrite(self.command_last_word_addr, [0x00,0x00,0x00,0x00])
        retval=self.readValue(1) #flush header response word
        self.getErrorCode(retval[0])
        
    def reconfigure(self, application_offset_address):
        command = [0x01, 0x00, 0x20,  0x5C]
        print('reconfigure..')
        self.spi.systemAccessWrite(self.command_addr, command)
        self.spi.systemAccessWrite(self.command_addr, convertWordToList(application_offset_address)) #address [31:0], from programming file generation
        self.getFifoFreeSpace()
        self.spi.systemAccessWrite(self.command_last_word_addr, [0x00, 0x00, 0x00, 0x00]) #address[63:32]-should be all 0's

        self.getFifoFreeSpace()
        print(self.readValue(1))

    def getConfigStatus(self):
        command = [0x03,0x00,0x00,0x04]
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.getFifoFreeSpace()
        retval=self.readValue(7)
        return retval

    def getRSUStatus(self):
        command = [0x07,0x00,0x00,0x5B]
        self.spi.systemAccessWrite(self.command_last_word_addr, command)
        self.getFifoFreeSpace()
        retval=self.readValue(10)
        return retval
    
    def getCoreTemps(self):
        command = [0x02, 0x00, 0x10,  0x19]
        #print('getting temp..')
        self.spi.systemAccessWrite(self.command_addr, command)
        self.spi.systemAccessWrite(self.command_last_word_addr, [0x00, 0x01, 0x00, 0x3C]) 
        #self.getFifoFreeSpace()
                
        retval = self.readValue(5)[1:4]
        temps=[]
        for i in range(len(retval)):
            val = (0xFF & retval[i][5]) | ((0xFF & retval[i][4]) << 8) | ((0xFF & retval[i][3]) << 16)
            temps.append(val * 1./256)
        return temps

    def qspiRead(self, address, num_words):
        #SDM mailbox FIFO is 256 words limited
        ##########
        _num_words = 0xFF & num_words
        self.qspiOpen()
        self.qspiChipSelect()
        command = [0x0C,0x00,0x20,0x3A]
        self.spi.systemAccessWrite(self.command_addr, command) #header
        self.spi.systemAccessWrite(self.command_addr, address)
        self.spi.systemAccessWrite(self.command_last_word_addr, [0x00,0x00,0x00,_num_words])

        time.sleep(0.2)
        retval = self.readValue(_num_words+1)
        self.qspiClose()
        return retval

    def qspiWrite(self, address, data):
        #SMD mailbox FIFO limited to 256 words
        #data in an array of 4-byte lists
        ####
        self.qspiOpen()
        self.qspiChipSelect()
        cmd_length = len(data) + 2
        #print('qspiWrite length',cmd_length)
        command = [0x0D,0x00 | ((cmd_length & 0xF0) >> 4),0x00 | ((cmd_length & 0xF) << 4),0x39]
        self.spi.systemAccessWrite(self.command_addr, command) #write header
        self.spi.systemAccessWrite(self.command_addr, address) #write flash address offet
        self.spi.systemAccessWrite(self.command_addr, [0x00, 0x00, 0x00, 0xFF & len(data)])
        if len(data) > 1:
            for i in range(cmd_length-3):
                self.spi.systemAccessWrite(self.command_addr, data[i])
            self.spi.systemAccessWrite(self.command_last_word_addr, data[-1])
        else:
            self.spi.systemAccessWrite(self.command_last_word_addr, data[0])

        time.sleep(0.002)
        retval = self.readValue(1)
        self.qspiClose()
        return retval
                                       
    def qspiEraseSector(self, address):
        #erase 64KB sectors at a time
        # add check to avoid erasure of any offset addresses less than first application image
        #####
        if convertListToWord(address, spibytes=False) < convertListToWord(self.CPB1_offset_addr, spibytes=False):
            print('do not erase here, nothing was done')
            return 1

        self.qspiOpen()
        self.qspiChipSelect()
        command = [0x0B,0x00,0x20,0x38]
        
        self.spi.systemAccessWrite(self.command_addr, command) #header
        self.spi.systemAccessWrite(self.command_addr, address)#first data word, offset address, 64KB-aligned
        self.spi.systemAccessWrite(self.command_last_word_addr, [0x00,0x00,0x40,0x00]) #erase 64KB sectors
        time.sleep(0.2) #erase time buffer for flash
        retval=self.readValue(1) #flush header readback
        
        self.qspiClose()
        return retval

def dumpDidaqInfo(dev, filename='info_didaq.json'):

    _fw_version = dev.spi.getFwVersion()
    firmware_date = str((_fw_version[0] << 4) | ((_fw_version[1] & 0xF0) >> 4))+'.'+str(_fw_version[1] & 0x0F)
    firmware_version = str((_fw_version[3] & 0xF0)>>4)+str('.')+str(_fw_version[3] & 0x0F)
    chip_id = dev.getChipID()
    jtag_id = dev.getID()
    core_temps = dev.getCoreTemps()
    config_stat = dev.getConfigStatus()
    _config_err = convertListToWord(config_stat[1])
    _quart_version = str(config_stat[2][3])+'.'+str(config_stat[2][4])+'.'+str(config_stat[2][5])

    _appl_img_addr = dev.CPB0_offset_addr
    _appl_img_addr[3] = 0x20
    application_image0_addr = convertListToWord(dev.qspiRead(_appl_img_addr, 1)[1])
    _appl_img_addr[3] = 0x28
    application_image1_addr = convertListToWord(dev.qspiRead(_appl_img_addr, 1)[1])
    
    rsu_stat = dev.getRSUStatus()
    _running_fw_offset_addr = hex(convertListToWord(rsu_stat[1]))
    _failing_fw_image_addr = hex(convertListToWord(rsu_stat[3]))
    _rsu_state_error = [rsu_stat[5],rsu_stat[6]]
    
    info_dict={}
    info_dict['fw_ver']=[firmware_date, firmware_version]
    info_dict['ids']=[hex(chip_id), hex(jtag_id)]
    info_dict['temps']=core_temps
    info_dict['config_err']=_config_err
    info_dict['quartus_ver']=_quart_version
    info_dict['running_fw_addr']=_running_fw_offset_addr
    info_dict['failing_fw_addr']=_failing_fw_image_addr
    info_dict['rsu_state_error']=_rsu_state_error
    info_dict['application0_pointer_addr']=hex(application_image0_addr)
    info_dict['application1_pointer_addr']=hex(application_image1_addr)
    
    with open(filename, 'w') as f:
        json.dump(info_dict, f)


def convertListToWord(byte_list,spibytes=True):
    '''4byte list to 32bit word, note spi read returns 6 bytes, first two are 0x00'''
    if spibytes:
        word = (byte_list[2] << 24) | (byte_list[3] << 16) | (byte_list[4] << 8) | byte_list[5]
    else:
        word = (byte_list[0] << 24) | (byte_list[1] << 16) | (byte_list[2] << 8) | byte_list[3]
    return word

def convertWordToList(word):
    '''32bit word to big endien 4-byte list'''
    byte_list = [(word & 0xFF000000) >> 24, (word & 0x00FF0000) >> 16, (word & 0x0000FF00) >> 8, (word & 0x000000FF)]
    return byte_list


if __name__=="__main__":

    didaq = Didaq()
    print('fw_version:', didaq.getFwVersion())
    #print('board_version:', didaq.getBoardVersion()[3])

    sdm = SDM_SPI()

    print(sdm.getCoreTemps())
    dumpDidaqInfo(sdm)





import didaq
import sys
import time
import math

#####################
## application image offset address in QSPI
TARGET_START_ADDR = 0x01000000
#####################
filename = 'fw/output_file.rpd' #'fw/didaqfw_0xe3000030.rpd'
file_offset_address = 0x00000000

WRITE_BYTES_PER_TRANSACTION = 512 ###128 words
ERASE_SECTOR_SIZE = 0x4000 * 4 ##byte address


def writeImage(dev, filename, erase=True):

    start_time = time.time()
    with open(filename, 'rb') as bin_file:
        bin_file.seek(0,2)
        num_bytes = bin_file.tell()
        flash_end_address = TARGET_START_ADDR + num_bytes

        if erase:
            ##--------------------------------
            ##ERASE
            print('erasing application image at: ', hex(TARGET_START_ADDR), '......')
            for i in range(math.ceil(num_bytes/ERASE_SECTOR_SIZE)):
                current_flash_erase_offset_addr = ERASE_SECTOR_SIZE * i + TARGET_START_ADDR
                retval=dev.qspiEraseSector(didaq.convertWordToList(current_flash_erase_offset_addr))

                #print(i,hex(current_flash_erase_offset_addr),retval)
            print('.... done with erase')

        ##--------------------------------
        ##WRITE
        print('writing application image at: ', hex(TARGET_START_ADDR), '......')
        num_write_cycles = int(num_bytes / WRITE_BYTES_PER_TRANSACTION) #hopefully an integer

        bin_file.seek(0,0) #back to beginning of rpd file

        file_current_addr = file_offset_address
        bin_file.seek(file_current_addr)

        ##loop over write cycles
        for i in range(num_write_cycles):

            qspi_address = TARGET_START_ADDR + WRITE_BYTES_PER_TRANSACTION * i ##byte address
            write_chunk = []
            chunk = bin_file.read(512)
            
            ##each write cycle has 128 words written to QSPI via the SDM mailbox
            for j in range(128):
                #_word = bin_file.read(4)
                #write_chunk.append([_word[3],_word[2],_word[1],_word[0]])
                write_chunk.append([chunk[j*4+3],chunk[j*4+2],chunk[j*4+1],chunk[j*4]])
                
            retval=dev.qspiWrite(didaq.convertWordToList(qspi_address), write_chunk)
            if dev.getErrorCode(retval[0]) == 1:
                print('error',i,num_write_cycles,hex(qspi_address),len(write_chunk),write_chunk[0],retval,0x0D)

        elapsed_time = time.time() - start_time
        print('.... done with image write, in', int(elapsed_time), 'seconds')
        


if __name__=="__main__":
    
    didaq_sdm = didaq.SDM_SPI()
    writeImage(didaq_sdm, filename)

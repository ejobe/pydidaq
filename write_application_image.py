import didaq
import sys
import time
import math

TARGET_START_ADDR = 0x01000000
filename = 'fw/didaqfw_0xe3000030.rpd'

WRITE_BYTES_PER_TRANSACTION = 512 ###128 words
ERASE_SECTOR_SIZE = 0x4000 * 4 ##byte address


def writeImage(dev, filename):

    start_time = time.time()
    with open(filename, 'rb') as bin_file:
        bin_file.seek(0,2)
        num_bytes = bin_file.tell()
        flash_end_address = TARGET_START_ADDR + num_bytes

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
        print(num_bytes/WRITE_BYTES_PER_TRANSACTION)
        #for i in range(math.ceil(num_bytes/WRITE_BYTES_PER_TRANSACTION))


        


if __name__=="__main__":
    
    didaq_sdm = didaq.SDM_SPI()
    writeImage(didaq_sdm, filename)

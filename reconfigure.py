import didaq

if __name__=="__main__":
    didaq_sdm = didaq.SDM_SPI()
    print('this script will hang.. reconfiguring application image..')
    didaq_sdm.reconfigure(0x01000000)
    

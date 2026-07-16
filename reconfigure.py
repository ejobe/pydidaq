import didaq

def reconfigure(adr=0x01000000):
    didaq_sdm=didaq.SDM_SPI()

if __name__=="__main__":
    didaq_sdm = didaq.SDM_SPI()
    print('this script will hang.. reconfiguring application image..')
    didaq_sdm.reconfigure(0x01000000)
    

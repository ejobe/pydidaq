import didaq_debug

if __name__=="__main__":
    didaq_sdm = didaq_debug.SDM()
    print('this script will hang.. reconfiguring application image..')
    didaq_sdm.reconfigure()
    

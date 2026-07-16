import didaq_serial.didaq_i2c as didaq_i2c
import didaq_serial.didaq_adc_config as adc_config
import time
import numpy
import didaq #spi-interface
import didaq_data_spi
import json

directory = 'info/'

print('starting didaq.... if hangs for more than 5 sec at start may need to do a USBHUB_RESET via the console ')

pll = didaq_i2c.PLLConfig()
pll.configure()
time.sleep(1)

align=False
tries=0
while((not align) or (tries > 3)):

    didaq_sdm = didaq.SDM_SPI()
    didaq_sdm.reconfigure(0x01000000)
    time.sleep(2)

    didaq.dumpDidaqInfo(didaq_sdm, directory+'info_didaq.json')
    with open(directory+'info_didaq.json', 'r') as f:
        info = json.load(f)

    print('application firmware ver', info['fw_ver'], 'at', info['running_fw_addr']) 
    print('......')
    print('starting up ADC and data')

    time.sleep(1)
    
    adc_config.run()
    dat = didaq_data_spi.takeEvent(cal_pulse=True, filename=directory+'aligntest.dat')

    align_vector=[]
    for i in range(24):
        align_vector.append(numpy.where(dat[i,100:] > 135)[0][0])

    print('edges:', align_vector)
    all_edges_identical = (align_vector == align_vector[0]).all()

    if all_edges_identical:
        align=True

    tries=tries+1
    
if tries > 3:
    print('maybe some issue')

print('----------------------')
print('didaq setup done')
print('----------------------')



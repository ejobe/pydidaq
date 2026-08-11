#! /usr/bin/env python3

import didaq_serial.didaq_i2c as didaq_i2c
import didaq_serial.didaq_adc_config as adc_config
import time
import numpy
import didaq #spi-interface
import didaq_data_spi
import json
import os
import argparse


parser = argparse.ArgumentParser('startup_didaq', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-f', '--fs_range', type=lambda x: int(x, 0), nargs=6,
                    choices=[0xFFFF, 0xA000, 0x2000],
                    metavar=('adc0', 'adc1', 'adc2', 'adc3', 'adc4', 'adc5'),
                    help='full-scale range register setting per ADC, decimal or\n'
                         '0x-prefixed hex. Possible choices:\n'
                         '  0xFFFF (65535) -> 1000 mVpp\n'
                         '  0xA000 (40960) ->  800 mVpp\n'
                         '  0x2000 ( 8192) ->  500 mVpp\n'
                         '(default: 0xFFFF for all ADCs)')
args = parser.parse_args()

directory = 'info/' if "DIDAQ_INFO_DIR" not in os.environ else os.environ['DIDAQ_INFO_DIR'] + '/'

print('starting didaq.... if hangs for more than 5 sec at start may need to do a USBHUB_RESET via the console ')

pll = didaq_i2c.PLLConfig()
pll.configure()
time.sleep(1)

align=False
tries=0
while((not align) and (tries < 3)):

    time.sleep(1)
    adc_config.off()
    time.sleep(1)

    didaq_sdm = didaq.SDM_SPI()
    didaq_sdm.reconfigure(0x01000000)
    time.sleep(3)

    didaq.dumpDidaqInfo(didaq_sdm, directory+'info_didaq.json')
    with open(directory+'info_didaq.json', 'r') as f:
        info = json.load(f)

    print('application firmware ver', info['fw_ver'], 'at', info['running_fw_addr'])
    print('......')
    print('starting up ADC and data')

    time.sleep(1)
    adc_config.run(adc_fs_ranges=args.fs_range)
    time.sleep(5)
    dat_spit = didaq_data_spi.takeEvent(cal_pulse=True, filename=directory+'dump.dat')
    dat = didaq_data_spi.takeEvent(cal_pulse=True, filename=directory+'aligntest.dat')

    align_vector=[]
    for i in range(24):
        align_vector.append(numpy.where(dat[i,100:] < 122)[0][0])

    print('edges:', align_vector)
    #all_edges_identical = (align_vector == align_vector[0]).all()
    all_edges_identical = numpy.all(numpy.abs(align_vector-align_vector[0]) <=1)

    if all_edges_identical:
        align=True

    tries=tries+1

if tries >= 3:
    print('maybe some issue')

print('----------------------')
print('didaq setup done')
print('----------------------')

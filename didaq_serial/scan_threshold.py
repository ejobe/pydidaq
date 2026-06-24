import didaq_debug
import time
import didaq_rf_trig as rf_trigger
import numpy
import json

trig = rf_trigger.Trig()
trig.setCoinc(0, enable=0)
trig.setCoincThresholds()

trig.setBeamThresholds(4000)
trig.setBeamformer(enable=1, window=1)

scaler_array={}
scaler_array['thresh']=[]
scaler_array['scalers']=[]

for i in range(800, 1300, 25): 
    trig.setBeamThresholds(i)
    print('setting thresholds ', i)
    time.sleep(15)
    scalers=trig.readScalers(verbose=False)
    scaler_array['thresh'].append(i)
    scaler_array['scalers'].append(scalers)



with open("threshold_scan.json", "w") as file:
    json.dump(scaler_array, file)

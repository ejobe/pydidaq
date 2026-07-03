import didaq
import time

sdm = didaq.SDM_SPI()

t = time.time()
while(True):
    time.sleep(30)
    print(time.time()-t, sdm.getCoreTemps())


"""
This file provides an example of how to get data from thingsboard database
This can be extended to the fleet database with the same exact approach
"""


import requests, json, sys, logging, numpy as np, datetime, matplotlib.pyplot as plt, math, pandas as pd, time

headersToken = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}


PROTOCOL, IP, PORT =  'http', 'watt.linksfoundation.com', '8080' 
url_auth = PROTOCOL + '://' + IP + ':' + PORT + '/api/auth/login'
user, password =    'hamidreza.mirtaheri@linksfoundation.com', 'Hamidreza41321360'

data = '{"username":"'+user+'", "password":"'+password+'"}'

try:
    authResponse = requests.post(url=url_auth, headers=headersToken, data=data)
    print(authResponse)
    headers = {'Accept':'application/json','X-Authorization': 'Bearer '+ authResponse.json()['token']}

    
except Exception as error:
    print('it failed because of : {}'.format(error))

DEVICE = 'd9a5dbd0-bd24-11eb-9909-c96dc06c86ee' # Cabina Caio Mario

INTERVAL = '600000'
LIMIT = '50000000'
AGG = 'NONE'


startTimeDt  = datetime.datetime(2022, 7, 1, 10, 0)
endTimeDt    = datetime.datetime(2022, 7, 1, 10, 30) 

startTimeEpoch = round(datetime.datetime.timestamp(startTimeDt)*1000)
endTimeEpoch   = round(datetime.datetime.timestamp(endTimeDt)*1000) 

startTs = str(startTimeEpoch)  
endTs   = str(endTimeEpoch) 



keys='voltage,current' 

url_query = PROTOCOL+"://"+IP+":"+PORT+"/api/plugins/telemetry/DEVICE/"+DEVICE+"/values/timeseries?interval="+INTERVAL+"&limit="+LIMIT+"&agg="+AGG+"&keys="+keys+"&startTs="+startTs+"&endTs="+endTs

try:
    
    response = requests.get(url_query,headers=headers)
    print(response)

except Exception as error:
    print('Attempet failed because of {}'.format(error))



retreivedData = response.json()


TS = np.array([datetime.datetime.fromtimestamp(t['ts']/1000) for t in retreivedData[keys.split(",")[0]]])
DB_DATA = np.array([[float(v['value']) for v in val] for val in retreivedData.values()]).T


# DB_DATA_CORRECTED = np.flip(DB_DATA, axis=0)
# DB_TS_CORRECTED   = np.flip(TS, axis=0)


FROM = 100
TO = FROM + 200
fig, ax1 = plt.subplots()
ax2 = ax1.twinx()
ax1.plot(DB_DATA[:,0][FROM:TO], c='r')
ax2.plot(DB_DATA[:,1][FROM:TO], c='b')
ax1.legend(["voltage"])
ax2.legend(["current"])
plt.show()

# crea un .csv con i dati di corrente e tensione 
df = pd.DataFrame(index=TS, data=DB_DATA, columns=['Voltage', 'Current'])
df.to_csv("Latest Data Substation.csv")



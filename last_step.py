from typing import TYPE_CHECKING
import pandas as pd
import os
import numpy as np
from pandas.core import groupby
def Filter():
    path =r"/Users/sunyenpeng/Desktop/python/cooperation"
    dirs = os.listdir(path)
    win = []
    for file in dirs:
        data = pd.read_csv('.//data//download//' + file, encoding='UTF-8')
        Stock_volume = np.sum(data['Buy in'].astype(int))+np.sum(data['Sold out'].astype(int))

        group = data.groupby('Stock Seller')
        l = group.size().index

        record = {}
        for seller in l:
            new_df = group.get_group(seller)
            Totalbuyin = np.sum(new_df['Buy in'].astype(float)).astype(float)
            Totalsoldout =np.sum(new_df['Sold out'].astype(float)).astype(float)
            Substraction = Totalbuyin -Totalsoldout
            record[seller] = Substraction
            print(Substraction)
        record = sorted(record.values(), reverse=True)
        record = np.asarray(record)
        
        max_ten_record = record[:10]
        min_ten_record = record[-10:]
        
        for i in range(len(min_ten_record)):
            min_ten_record[i] = abs(min_ten_record[i])
        

        if (sum(max_ten_record) - sum(min_ten_record))> 0 and \
            sum(max_ten_record)>0.3*Stock_volume:
            win.append(file.split('_')[0])

    win = pd.DataFrame(win, columns=['Stock_Codes'])
    win.to_csv('Filtered_Stock.csv',index=False)

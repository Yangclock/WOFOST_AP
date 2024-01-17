import os
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from utils import kalman_filter
from utils import sg_envelope_filter

if __name__ == '__main__':
    data_dir = r'D:\\Desktop\\WOFOST_AP\\workspace'  # 工作路径
    txttable = pd.read_excel(os.path.join(data_dir, 'LAI_modis.xlsx'), sheet_name='Sheet1')
    zz = np.array(txttable.iloc[:, 1])  # 原始数据
    res_sg = sg_envelope_filter(zz, 3, 0.08, 1)
    res_kalman = kalman_filter(zz)

    # 可视化两个效果
    plt.plot(zz, 'g', label='noisy measurements')  # 真实值
    plt.plot(res_sg, 'r', label='sg estimate')  # sg 估计值
    plt.plot(res_kalman, 'b-', label='kalman estimate')  # kl 估计值
    plt.legend()
    plt.show()

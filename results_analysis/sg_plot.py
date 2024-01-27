import os
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from utils import kalman_filter
from utils import sg_envelope_filter

if __name__ == '__main__':
    data_dir = r'D:\\Desktop\\WOFOST_AP\\\workspace\\LAI'  # 工作路径
    txttable = pd.read_excel(os.path.join(data_dir, 'crop_LAI_MODISs2.xlsx'), sheet_name='Sheet2')
    summary_output = {}
    for index, row in txttable.iterrows():
        zz = np.array(row[1:])  # 原始数据
        res_sg = sg_envelope_filter(zz, 3, 0.5, 1)
        res_sg = pd.Series(res_sg)
        summary_output.update({index: res_sg})
    summary_output = pd.DataFrame(summary_output)
    summary_output.to_excel(os.path.join(data_dir, 'rice_LAI_SG.xlsx'))

    # res_kalman = kalman_filter(zz)

    # # 可视化两个效果
    # plt.plot(zz, 'g', label='noisy measurements')  # 真实值
    # plt.plot(res_sg, 'r', label='sg estimate')  # sg 估计值
    # plt.plot(res_kalman, 'b-', label='kalman estimate')  # kl 估计值
    # plt.legend()
    # plt.show()

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


# #导入需要的库
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
#
#
# def main():
#     """
#     主函数
#     """
# 	sns.set_style('whitegrid',{'font.sans-serif': ['simhei','Arial']})
# 	data = pd.read_csv("C:\\Users\\WIN10\\Desktop\\数据分析\\SPAD1.csv",encoding = "gbk",engine = 'python')#读取数据
# 	fig_q2 = plt.figure(figsize = (4,5))#创建图表
# 	#计算成透视表
# 	y1 = data.pivot_table('花后15天', index='品种', columns='氮水平', aggfunc='mean')
# 	y2 = data.pivot_table('拔节SPAD', index='品种', columns='氮水平', aggfunc='mean')
# 	y3 = data.pivot_table('开花SPAD', index='品种', columns='氮水平', aggfunc='mean')
# 	y4 = data.pivot_table('花后30天', index='品种', columns='氮水平', aggfunc='mean')
# 	#绘图
# 	h = sns.heatmap(y2, annot=True, cmap='Greens', fmt='.2f', vmin=25, vmax=55, annot_kws={'size':16},cbar=False)
# 	plt.title('BS', fontsize=18)
# 	plt.tick_params(labelsize=16)
# 	plt.xlabel('Nitrogen rates',fontdict={'size': 16})
# 	plt.ylabel('varieties',fontdict={'size': 16})
# 	cb = h.figure.colorbar(h.collections[0])  # 显示colorbar,此种方法需要先关闭cbar
# 	cb.ax.tick_params(labelsize=16)  # 设置colorbar刻度字体大小。
# 	plt.show()
# 	# http://seaborn.pydata.org/generated/seaborn.heatmap.html 热图的介绍
#
# if __name__ == '__main__':
#     main()```
#

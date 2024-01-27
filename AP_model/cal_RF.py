import os
import sklearn
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')
from sklearn import metrics
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
from sklearn.model_selection import cross_val_predict
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from scipy.stats import gaussian_kde
from scipy import optimize
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib import rcParams
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False



def rf_nocrop():
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "no_crop_model")  # 工作路径
    re_dir = os.path.join(data_dir, "result")
    data = pd.read_excel(os.path.join(work_dir, "model_variables.xlsx"), sheet_name='Sheet1')
    x = data.iloc[:, 5:55]
    y = data.AP2020
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=0)  # 划分训练集和测试集9:1
    estimators_max_score = 1000
    depth_max_score = 3
    features_max_score = 1
    rfc = RandomForestRegressor(n_estimators=estimators_max_score, max_depth=depth_max_score,
                                max_features=features_max_score, oob_score=True, random_state=0)
    rfc.fit(x_train, y_train)  # 拟合训练集，训练模型
    y_train_pre = rfc.predict(x_train)
    y_test_pre = rfc.predict(x_test)  # 预测y值
    print('score:', rfc.score(x_test, y_test))  # 输出得分
    print('oob_score:', rfc.oob_score_)  # 输出oob得分
    print('oob_prediction:', rfc.oob_prediction_)  # 输出oob预测
    print('rfc_test prediction:', y_test_pre)  # 输出测试集预测值

    importances = rfc.feature_importances_ #特征重要性评估
    std = np.std([tree.feature_importances_ for tree in rfc.estimators_], axis = 0)  #标准化
    indices = np.argsort(importances)[::-1]
    print('Feature ranking')#标题
    zz = zip(importances,x,std)
    zzs = sorted(zz,key = lambda x:x[0],reverse = True)
    # labels = [x[1] for x in zzs]
    labels = [x_test.columns[indices[i]] for i in range(len(x_test.columns))]
    for i in range(min(20,x_train.shape[1])):
        print('%2d) %-*s %f' % (i + 1 , 30,x_test.columns[indices[i]],importances[indices[i]]))
    plt.figure(figsize=(12,6),dpi=100)  #设置绘图范围大小和分辨率
    fontdict1 = {"color":"k",'family':'Times New Roman'}  #默认字体和颜色
    plt.title('Feature Importance',fontsize = 17)#标题文字和大小
    plt.bar(labels,importances[indices],color = 'r',yerr = std[indices],align ='center')  #标题索引，颜色，位置
    plt.xticks(range(len(importances)),labels,rotation = 90)   #X标签，字体旋转90°
    plt.tick_params(labelsize=13)    #标签字体大小
    plt.xlabel('Feature',fontsize = 15) #x轴标题及大小
    plt.ylabel('Relative Impertance/%',fontsize = 15)#y轴标题及大小
    plt.xlim([-0.7, x_train.shape[1]]) #柱状体位置
    plt.gcf().subplots_adjust(left=0.2,top=0.91,bottom=0.3)
    plt.savefig(os.path.join(re_dir,'特征重要性.jpg'),dpi = 300, bbox_inche = 'tight',pad_inches=0.2)#保存
    plt.show()
    imp_pd = pd.DataFrame({
        "labels": labels,
        "importance": [importances[i] for i in indices]
    })
    imp_pd.to_excel(os.path.join(re_dir,'特征重要性.xlsx'))
    # 计算相应的MAE和RMSE，得到价格的平均绝对值损失
    print('RandomForestRegressor evaluating result:')
    print("测试集R2: ", np.corrcoef(y_test, y_test_pre)[0, 1] * np.corrcoef(y_test, y_test_pre)[0, 1])
    print("建模集R2: ", np.corrcoef(y_train, y_train_pre)[0, 1] * np.corrcoef(y_train, y_train_pre)[0, 1])
    print("Test MAE: ", metrics.mean_absolute_error(y_test, y_test_pre))
    print("Test RMSE: ", np.sqrt(metrics.mean_squared_error(y_test, y_test_pre)))
    Test_errors = abs(y_test_pre - y_test)
    Test_mape = 100 * (Test_errors / y_test)
    print('Test MAPE:', np.mean(Test_mape))


def rf_crop():
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "crop_model")  # 工作路径
    re_dir = os.path.join(data_dir, "result")
    data = pd.read_excel(os.path.join(work_dir, "model_variables.xlsx"), sheet_name='Sheet1')
    x = data.iloc[:, 5:]
    y = data.AP2020
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=0)  # 划分训练集和测试集9:1
    estimators_max_score = 1000
    depth_max_score = 3
    features_max_score = 1
    rfc = RandomForestRegressor(n_estimators=estimators_max_score, max_depth=depth_max_score,
                                max_features=features_max_score, oob_score=True, random_state=0)
    rfc.fit(x_train, y_train)  # 拟合训练集，训练模型
    y_test_pre = rfc.predict(x_test)  # 预测y值
    y_train_pre = rfc.predict(x_train)
    print('score:', rfc.score(x_test, y_test))  # 输出得分
    print('oob_score:', rfc.oob_score_)  # 输出oob得分
    print('oob_prediction:', rfc.oob_prediction_)  # 输出oob预测
    print('rfc_test prediction:', y_test_pre)  # 输出测试集预测值

    importances = rfc.feature_importances_  # 特征重要性评估
    std = np.std([tree.feature_importances_ for tree in rfc.estimators_], axis=0)  # 标准化
    indices = np.argsort(importances)[::-1]
    print('Feature ranking')#标题
    zz = zip(importances,x,std)
    zzs = sorted(zz,key = lambda x:x[0],reverse = True)
    # labels = [x[1] for x in zzs]
    labels = [x_test.columns[indices[i]] for i in range(len(x_test.columns))]
    for i in range(min(20,x_train.shape[1])):
        print('%2d) %-*s %f' % (i + 1 , 30,x_test.columns[indices[i]],importances[indices[i]]))
    plt.figure(figsize=(12,6),dpi=100)  #设置绘图范围大小和分辨率
    fontdict1 = {"color":"k",'family':'Times New Roman'}  #默认字体和颜色
    plt.title('Feature Importance',fontsize = 17)#标题文字和大小
    plt.bar(labels,importances[indices],color = 'r',yerr = std[indices],align ='center')  #标题索引，颜色，位置
    plt.xticks(range(len(importances)),labels,rotation = 90)   #X标签，字体旋转90°
    plt.tick_params(labelsize=13)    #标签字体大小
    plt.xlabel('Feature',fontsize = 15) #x轴标题及大小
    plt.ylabel('Relative Impertance/%',fontsize = 15)#y轴标题及大小
    plt.xlim([-0.7, x_train.shape[1]]) #柱状体位置
    plt.gcf().subplots_adjust(left=0.2,top=0.91,bottom=0.3)
    plt.savefig(os.path.join(re_dir,'特征重要性.jpg'),dpi = 300, bbox_inche = 'tight',pad_inches=0.2)#保存
    plt.show()
    imp_pd = pd.DataFrame({
        "labels": labels,
        "importance": [importances[i] for i in indices]
    })
    imp_pd.to_excel(os.path.join(re_dir,'特征重要性.xlsx'))
    # 计算相应的MAE和RMSE，得到价格的平均绝对值损失
    print('RandomForestRegressor evaluating result:')
    print("测试集R2: ", np.corrcoef(y_test, y_test_pre)[0, 1] * np.corrcoef(y_test, y_test_pre)[0, 1])
    print("建模集R2: ", np.corrcoef(y_train, y_train_pre)[0, 1] * np.corrcoef(y_train, y_train_pre)[0, 1])
    print("Test MAE: ", metrics.mean_absolute_error(y_test, y_test_pre))
    print("Test RMSE: ", np.sqrt(metrics.mean_squared_error(y_test, y_test_pre)))
    Test_errors = abs(y_test_pre - y_test)
    Test_mape = 100 * (Test_errors / y_test)
    print('Test MAPE:', np.mean(Test_mape))


if __name__ == "__main__":
    rf_nocrop()

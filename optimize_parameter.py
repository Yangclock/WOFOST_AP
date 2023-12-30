import os
import datetime
import pandas as pd
from pcse.fileinput import CABOFileReader  # 读取CABO文件（作物土壤文件）
from pcse.fileinput import YAMLAgroManagementReader  # 管理文件读取
from pcse.models import Wofost71_WLP_FD, Wofost71_PP  # 导入模型，Wofost71_PP潜在模型
from pcse.base import ParameterProvider  # 综合作物、土壤、位点参数
from pcse.fileinput import ExcelWeatherDataProvider  # 读取气象文件
import numpy as np
import nlopt

site = '1'  # 位点
variety = 103  # 品种
data_dir = r'E:\2022.11.21毕业论文\3实验过程\WOFOST有效磷\test' # 模型校准文件夹
data_base_info = pd.read_excel('LAI校准.xlsx', sheet_name='基本情况')
sub_data = data_base_info.loc[data_base_info['试验地']==site, 
                              ['经度', '维度', '品种', '播量（计算）', '播种期', 
                               'sa', 'cl', 'bd', 'som', '灌溉']]
# 基本数据获取
lon = sub_data.loc[sub_data['品种']==variety, ['经度']]  # 读取经度
lat = sub_data.loc[sub_data['品种']==variety, ['维度']]  # 读取纬度
SAND = sub_data.loc[sub_data['品种']==variety, ['sa']].iloc[0,0]  # 砂粒
CLAY = sub_data.loc[sub_data['品种']==variety, ['cl']].iloc[0,0]  # 黏粒
OM = sub_data.loc[sub_data['品种']==variety, ['som']].iloc[0,0]  # 有机质
BULK_DENSITY = sub_data.loc[sub_data['品种']==variety, ['bd']].iloc[0,0]  # 容重
sow_date = sub_data.loc[sub_data['品种']==variety, ['播种期']].iloc[0,0]  # 播期
irrigation = sub_data.loc[sub_data['品种']==variety, ['灌溉']].iloc[0,0]  # 灌溉条件

weather_dir = r'C:\Users\Administrator\Desktop\2020气象数据'  # 气象数据路径
cropdata = CABOFileReader(os.path.join(data_dir,'%d.CAB'%variety))  # 读取作物文件
soildata = CABOFileReader(os.path.join(data_dir,'EC3.NEW'))  # 土壤文件
sitedata = {'SSMAX'  : 0.,
            'IFUNRN' : 0,
            'NOTINF' : 0,
            'SSI'    : 0,
            'WAV'    : 30,
            'SMLIM'  : 0.03,
           'RDMSOL'  : 120}
parameters = ParameterProvider(cropdata=cropdata, soildata=soildata, sitedata=sitedata)  # 参数集合
# 数据替换
parameters['TDWI'] = sub_data.loc[sub_data['品种']==variety, ['播量（计算）']].iloc[0,0]  # 播量
parameters['SMW'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[0]  # 萎蔫点
parameters['SMFCF'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[1]  # 田间持水量
parameters['SM0'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[2]  # 饱和含水量
agromanagement = YAMLAgroManagementReader(os.path.join(data_dir,'wheatautoirrigation.agro'))  # 管理文件读取
agromanagement[0][datetime.date(2019, 10, 1)]['CropCalendar']['crop_start_date'] = sow_date  # 播期替换
irr_condition = agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['events_table'][0]  # 获取到自动灌溉的字典
irr_calculation = round(irrigation/100*parameters['SMFCF'], 2).item()  # 灌溉条件替换, 读取的数据可能是numpy类型
agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['events_table'][0][irr_calculation] = \
agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['events_table'][0].pop(list(irr_condition.keys())[0])
# 气象数据
weatherdataprovider = ExcelWeatherDataProvider(os.path.join(weather_dir,'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.
                                                            format(st_loc(lat.iloc[0,0]), st_loc(lon.iloc[0,0]))))
wf = Wofost71_WLP_FD(parameters, weatherdataprovider, agromanagement)  # 定义模型
wf.run_till_terminate()  # 运行模型直到终止
output=pd.DataFrame(wf.get_output()).set_index('day')



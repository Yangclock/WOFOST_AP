import os
import datetime
import pandas as pd
from pcse.base import ParameterProvider  # 参数整合
from pcse.fileinput import CABOFileReader  # 导入CABO格式数据
from pcse.fileinput import ExcelWeatherDataProvider  # 导入Excel气象数据
from pcse.fileinput import YAMLAgroManagementReader  # 导入YAML管理数据
from pcse.fileinput import YAMLCropDataProvider  # 导入YAML作物模型

# --------------------------------------------------------
#                     构建模型参数
# --------------------------------------------------------
# 模型
from pcse.models import Wofost80_NWLP_FD_beta
from pcse.models import Wofost80_PP_beta
# 导入通用的实用工具函数
from utils import st_loc  # 规范化经纬度至0.5°
from utils import argo_r_modify  # 修改施肥灌溉等管理参数
from utils import set_site_data  # 设置站点数据
from utils import jd_to_time  # 转换儒略日

# 路径设置
data_dir = r'D:\\Desktop\\WOFOST_AP\\workspace'  # 工作路径
weather_dir = r'D:\Desktop\WOFOST_AP\parameters\meteorological_parameter'  # 气象数据路径
crop_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\crop_parameter'  # 作物文件路径
soil_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\soil_parameter'  # 土壤文件路径
management_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\management_parameter'  # 管理文件路径
para_dir = r'D:\\Desktop\\WOFOST_AP\\simlab_sensitivity_analysis'  # simlab输出的参数读取
start = datetime.datetime.now()

data_base_info = pd.read_excel(os.path.join(para_dir, 'sensitive_sample_point.xlsx'), sheet_name='Sheet1')  # 模拟的位置
row = data_base_info.loc[0]
# 要改变的单一值数据
change_data = {'TSUM1': 0, 'TSUM2': 1, 'TDWI': 2, 'RGRLAI': 3, 'SPAN': 6, 'TBASE': 7, 'CVL': 17, 'CVO': 18,
               'CVR': 19, 'CVS': 20, 'Q10': 21, 'RML': 22, 'RMO': 23, 'RMR': 24, 'RMS': 25, 'RDI': 37, 'RRI': 38,
               'RDMCR': 39, 'WAV': 40, 'SMLIM': 41, 'NAVAILI': 42, 'PAVAILI': 43, 'KAVAILI': 44}

crop_name = row['crop_name_summer']  # 作物名称
variety_name = row['variety_name_summer']  # 作物种类名称
crop_data = YAMLCropDataProvider(crop_parameter_dir)  # 作物参数读取
crop_data.set_active_crop(crop_name, variety_name)  # 设置当前活动作物
soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file'] + '.new'))  # 土壤参数读取
parameters = ParameterProvider(crop_data, soil_data,
                               set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 上述参数与站点参数打包
agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo_r.yaml')),
                               row)  # 管理参数读取
weather_data = ExcelWeatherDataProvider(
    os.path.join(weather_dir, 'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                 format(st_loc(row['lat']), st_loc(row['lon']))))

# --------------------------------------------------------
#                     敏感性结果输出分析
# --------------------------------------------------------
sim_paraments = [1720.712219, 587.9023404, 107.7603863, 0.008618302849, 0.0009956966997, 0.001833695365, 53.91103994,
                 6.94144705, 0.4254047168, 0.5401334627, 0.5702240495, 0.3539371876, 38.84542848, 40.66196511,
                 41.09753519, 0.0853053124, 0.9330512084, 0.7042504626, 0.6877900612, 0.7776174759, 0.7031217651,
                 1.883685192, 0.02046311438, 0.003117597732, 0.01464308397, 0.02032021602, 0.4215317051, 0.4807972584,
                 0.3165024697, 0.5982993794, 0.5665549498, 0.6076431349, 0.3648661798, 0.02083064444, 0.01803214257,
                 0.02091001952, 0.02078266075, 10.90212252, 1.229292865, 75.54908145, 22.9629072, 0.5716875786,
                 185.3170322, 11.32383211, 105.2795147, 211.9023086]
# 更改参数
for items, value in change_data.items():
    parameters[items] = sim_paraments[value]
parameters['SLATB'][5] = sim_paraments[4]
parameters['SLATB'][9] = sim_paraments[5]
parameters['KDIFTB'][3] = sim_paraments[8]
parameters['KDIFTB'][7] = sim_paraments[9]
parameters['EFFTB'][1] = sim_paraments[10]
parameters['EFFTB'][3] = sim_paraments[11]
parameters['AMAXTB'][1] = sim_paraments[12]
parameters['AMAXTB'][3] = sim_paraments[13]
parameters['AMAXTB'][5] = sim_paraments[14]
parameters['TMPFTB'][3] = sim_paraments[15]
parameters['TMPFTB'][5] = sim_paraments[16]
parameters['FRTB'][1] = sim_paraments[26]
parameters['FRTB'][3] = sim_paraments[27]
parameters['FRTB'][5] = sim_paraments[28]
parameters['FLTB'][3] = sim_paraments[29]
parameters['FLTB'][5] = sim_paraments[30]
parameters['FLTB'][7] = sim_paraments[31]
parameters['FLTB'][9] = sim_paraments[32]
parameters['FSTB'][3] = 1 - sim_paraments[29]
parameters['FSTB'][5] = 1 - sim_paraments[30]
parameters['FSTB'][7] = 1 - sim_paraments[31]
parameters['FSTB'][9] = 1 - sim_paraments[32]
parameters['RDRRTB'][5] = sim_paraments[33]
parameters['RDRRTB'][7] = sim_paraments[34]
parameters['RDRSTB'][5] = sim_paraments[35]
parameters['RDRSTB'][7] = sim_paraments[36]
sow_date = jd_to_time(round(sim_paraments[45])).replace(year=2020)
agromanagement[0][datetime.date(2020, 6, 1)]['CropCalendar']['crop_start_date'] = sow_date
wf = Wofost80_PP_beta(parameters, weather_data, agromanagement)
wf.run_till_terminate()
summary_output = wf.get_summary_output()
output = wf.get_output()
print(1)

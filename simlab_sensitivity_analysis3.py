import os
import datetime
import pandas as pd
from pcse.base import ParameterProvider  # 参数整合
from pcse.fileinput import CABOFileReader  # 导入CABO格式数据
from pcse.fileinput import ExcelWeatherDataProvider  # 导入Excel气象数据
from pcse.fileinput import YAMLAgroManagementReader  # 导入YAML管理数据
from pcse.fileinput import YAMLCropDataProvider  # 导入YAML作物模型

# --------------------------------------------------------
#                     基础参数设置
# --------------------------------------------------------
# 模型
from pcse.models import Wofost80_NWLP_FD_beta
# 导入通用的实用工具函数
from utils import st_loc  # 规范化经纬度至0.5°
from utils import argo_w_modify  # 修改施肥灌溉等管理参数
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

# --------------------------------------------------------
#                     敏感性分析
# --------------------------------------------------------
data_base_info = pd.read_excel(os.path.join(para_dir, 'sensitive_sample_point.xlsx'), sheet_name='Sheet1')  # 模拟的位置
row = data_base_info.loc[0]
# 要改变的单一值数据
change_data = {'TSUM1': 0, 'TSUM2': 1, 'TDWI': 2, 'RGRLAI': 3, 'SPAN': 6, 'TBASE': 7, 'CVL': 17, 'CVO': 18,
               'CVR': 19, 'CVS': 20, 'Q10': 21, 'RML': 22, 'RMO': 23, 'RMR': 24, 'RMS': 25, 'RDI': 38, 'RRI': 39,
               'RDMCR': 40, 'WAV': 41, 'SMLIM': 42, 'NAVAILI': 43, 'PAVAILI': 44, 'KAVAILI': 45}

crop_name = row['crop_name_winter']  # 作物名称
variety_name = row['variety_name_winter']  # 作物种类名称
crop_data = YAMLCropDataProvider(crop_parameter_dir)  # 作物参数读取
crop_data.set_active_crop(crop_name, variety_name)  # 设置当前活动作物
soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file'] + '.new'))  # 土壤参数读取
parameters = ParameterProvider(crop_data, soil_data,
                               set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 上述参数与站点参数打包
agromanagement = argo_w_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo_w.yaml')),
                               row)  # 管理参数读取
weather_data = ExcelWeatherDataProvider(
    os.path.join(weather_dir, 'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                 format(st_loc(row['lat']), st_loc(row['lon']))))

# 创建文档储存模型输出结果
with open(os.path.join(para_dir, 'result.txt'), 'a') as fp2:
    fp2.writelines(['4', '\n', 'LAI', '\n', 'TAGP', '\n', 'TWSO', '\n', 'RPuptake', '\n', 'time = no', '\n'])
    # 打开simlab输出的文档
    with open(os.path.join(para_dir, 'EFAST_wheat0110.SAM'), 'r') as fp:
        fp.readline()  # 第一行
        number = fp.readline()  # 第二行为生成参数个数
        fp.readline()  # 变量个数
        fp.readline()  # 0  此后开始读参数
        fp2.write(str(number))
        for i in range(int(number)):
            sim_paraments = list(map(float, fp.readline().split('\t')[:-1]))
            # 更改参数
            for iterm, value in change_data.items():
                parameters[iterm] = sim_paraments[value]
            parameters['SLATB'][1] = sim_paraments[4]
            parameters['SLATB'][3] = sim_paraments[5]
            parameters['KDIFTB'][1] = sim_paraments[8]
            parameters['KDIFTB'][3] = sim_paraments[9]
            parameters['EFFTB'][1] = sim_paraments[10]
            parameters['EFFTB'][3] = sim_paraments[11]
            parameters['AMAXTB'][1] = sim_paraments[12]
            parameters['AMAXTB'][3] = sim_paraments[13]
            parameters['AMAXTB'][5] = sim_paraments[14]
            parameters['TMPFTB'][1] = sim_paraments[15]
            parameters['TMPFTB'][3] = sim_paraments[16]
            parameters['FRTB'][1] = sim_paraments[26]
            parameters['FRTB'][9] = sim_paraments[27]
            parameters['FRTB'][11] = sim_paraments[28]
            parameters['FRTB'][13] = sim_paraments[29]
            parameters['FLTB'][1] = sim_paraments[30]
            parameters['FLTB'][5] = sim_paraments[31]
            parameters['FLTB'][7] = sim_paraments[32]
            parameters['FLTB'][9] = sim_paraments[33]
            parameters['FSTB'][1] = 1 - sim_paraments[30]
            parameters['FSTB'][5] = 1 - sim_paraments[31]
            parameters['FSTB'][7] = 1 - sim_paraments[32]
            parameters['FSTB'][9] = 1 - sim_paraments[33]
            parameters['RDRRTB'][3] = sim_paraments[34]
            parameters['RDRRTB'][7] = sim_paraments[35]
            parameters['RDRSTB'][3] = sim_paraments[36]
            parameters['RDRSTB'][7] = sim_paraments[37]
            agromanagement[0][datetime.date(2019, 10, 1)]['CropCalendar']['crop_start_date'] = jd_to_time(round(sim_paraments[46]))
            wf = Wofost80_NWLP_FD_beta(parameters, weather_data, agromanagement)
            wf.run_till_terminate()
            output = wf.get_summary_output()
            fp2.write(str(output[0]['TWSO'], '\t', str(output[0]['TAGP'], '\t', str(output[0]['TAGP'], '\t', str(output[0]['TAGP'])))
            fp2.write('\n')
            if i % 100 == 0:
                print(i)
end = datetime.datetime.now()
print('运行完成,共用时{}'.format(end - start))

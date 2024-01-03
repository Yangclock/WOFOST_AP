import pcse
import pandas as pd
import matplotlib
import yaml
import os
import datetime
#模型
from pcse.models import Wofost71_WLP_FD
from pcse.models import Wofost80_NWLP_FD_beta
#参数导入需要的函数
from load_soil_water_parameter import soil_data #根据质地计算土壤参数
from pcse.fileinput import YAMLCropDataProvider #导入YAML作物模型
from pcse.fileinput import YAMLAgroManagementReader #导入YAML管理数据
from pcse.fileinput import CABOFileReader #导入CABO格式数据
from pcse.fileinput import ExcelWeatherDataProvider #导入Excel气象数据
from pcse.base import ParameterProvider #参数整合

#--------------------------------------------------------
#                     基础参数设置
#--------------------------------------------------------
data_dir = r'D:\\Desktop\\WOFOST_AP\\workspace'                                   # 工作路径
weather_dir = r'D:\Desktop\WOFOST_AP\parameters\meteorological_parameter'         # 气象数据路径
crop_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\crop_parameter'             # 作物文件路径
soil_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\soil_parameter'             # 土壤文件路径
management_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\management_parameter' # 管理文件路径


def set_site_data(NAVAILI,PAVAILI,KAVAILI):
    '''
    设置站点参数
    NAVAILI::土壤中的有效氮
    PAVAILI::土壤中的有效磷
    KAVAILI::土壤中的有效钾
    '''
    sitedata = {'SSMAX'  : 0.,
                'IFUNRN' : 0,
                'NOTINF' : 0,
                'SSI'    : 0,
                'WAV'    : 30,
                'SMLIM'  : 0.3,
                'RDMSOL'  : 120,
                'CO2' : 360,
                'NAVAILI': NAVAILI,
                'PAVAILI': PAVAILI,
                'KAVAILI': KAVAILI,
                'NSOILBASE':10,
                'PSOILBASE':10,
                'KSOILBASE':10,
                'BG_N_SUPPLY': 0.09,
                'BG_K_SUPPLY': 0.09,
                'BG_P_SUPPLY': 0.09,
                'NSOILBASE_FR':0.025,
                'PSOILBASE_FR':0.025,
                'KSOILBASE_FR':0.025}
    return sitedata


def argo_modify(agro, row):
    '''
    修改播种日期，土壤施肥与灌溉数据
    argo :: 读取的管理参数字典
    row  :: 列表
    '''
    agro[0][datetime.date(2019,10,1)]['CropCalendar']['crop_start_date'] = datetime.datetime.strptime(row['wintercrop_start_date'], '%Y-%m-%d').date()  # 播期替换
    events_table = [["2019-10-01",0.4],
                    ["2020-01-15",0.3],
                    ["2020-04-01",0.3]]
    fert_table = [["N",row["N_winter_fertilizer"]],
                  ["P",row["P_winter_fertilizer"]],
                  ["K",row["K_winter_fertilizer"]]]
    k = 0
    for i in events_table:
        for j in fert_table:
            agro = fertilizer_modify(agro, row, i[0], k, j[0], i[1]*j[1])
        k += 1
    #irr_condition = agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['events_table'][0]  # 获取到自动灌溉的字典
    #irr_calculation = round(irrigation/100*parameters['SMFCF'], 2).item()  # 灌溉条件替换, 读取的数据可能是numpy类型
    #agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['eventsol_table'][0][irr_calculation] = \
    #agromanagement[0][datetime.date(2019, 10, 1)]['StateEvents'][0]['events_table'][0].pop(list(irr_condition.keys())[0])
    #agro[0][datetime.date(2019,10,1)]['TimedEvents'][0]['events_table']
    return agro


def fertilizer_modify(agro, row, date, events_no, fert_type, fert_amount):
    '''
    修改按时间变化的施肥量
    '''
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    agro[0][datetime.date(2019,10,1)]['TimedEvents'][1]['events_table'][events_no][date][fert_type+'_amount'] = fert_amount
    return agro


def st_loc(num):
    """
    选取气象数据的时候标准化输入为0.5的分辨率
    """
    import math
    if num-math.floor(num) <=0.25 or num-math.floor(num)>=0.75:
        result = round(num)
    elif 0.25 < num-math.floor(num) < 0.75:
        result = math.floor(num) + 0.5      
    return result


#--------------------------------------------------------
#                     WOFOST运行
#--------------------------------------------------------
data_base_info = pd.read_excel(os.path.join(data_dir,'sample_point.xlsx'), sheet_name='Sheet1')
for index, row in data_base_info.iterrows(): # 逐行读取点位信息并模拟
    crop_name = row['crop_name_winter']  # 作物名称
    variety_name = row['variety_name_winter']  # 作物种类名称
    crop_data = YAMLCropDataProvider(crop_parameter_dir) # 作物参数读取
    crop_data.set_active_crop(crop_name, variety_name) # 设置当前活动作物
    soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file']+'.new'))  # 土壤参数读取
    parameters = ParameterProvider(crop_data, soil_data, set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 上述参数与站点参数打包
    agromanagement = argo_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo.yaml')), row) # 管理参数读取
    weather_data = ExcelWeatherDataProvider(os.path.join(weather_dir,'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                                                            format(st_loc(row['lat']), st_loc(row['lon']))))
    wf = Wofost80_NWLP_FD_beta(parameters, weather_data, agromanagement)  # 定义模型
    wf.run_till_terminate()  # 运行模型直到终止
    output = pd.DataFrame(wf.get_output()).set_index('day') # 获取输出结果
    file_name = 'wofost_result' + row['序号'] + '.xlsx' # 输出excel表的文件名
    output.to_excel(os.path.join(data_dir,file_name)) # 将结果输出为excel表
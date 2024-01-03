# 敏感性分析
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

start = datetime.datetime.now()
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
#                     基础参数设置
#--------------------------------------------------------
data_dir = r'D:\\Desktop\\WOFOST_AP\\workspace'                     # 工作路径
weather_dir = r'D:\Desktop\WOFOST_AP\parameters\meteorological_parameter' # 气象数据路径
crop_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\crop_parameter'     # 作物文件路径
soil_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\soil_parameter'     # 土壤文件路径
management_parameter_dir = 'D:\Desktop\WOFOST_AP\parameters\management_parameter' # 管理文件路径
para_dir = r'D:\\Desktop\\WOFOST_AP\\simlab_sensitivity_analysis'  # simlab输出的参数读取
data_base_info = pd.read_excel(os.path.join(data_dir,'sample_point.xlsx'), sheet_name='Sheet1') # 模拟的位置
row = data_base_info.iloc[0].tolist()

# 创建播种日期的字典
sow_date = dict(zip([i+1 for i in range(30)],[datetime.date(2019,10,i+1) for i in range(30)] ))
# 要改变的数据
change_data = {'TBASEM':0,'TEFFMX':1,'TDWI':2,'LAIEM':3,'RGRLAI':4,'SPAN':8,'TBASE':9,'CVL':15,'CVO':16,'CVR':17,
               'CVS':18,'Q10':19,'RML':20,'RMO':21,'RMR':22,'RMS':23,'PERDL':24,'CFET':27,'DEPNR':28,'RDI':29,
              'RRI':30,'RDMCR':31,'IFUNRN':32,'NOTINF':33,'SSI':34,'WAV':35,'SMLIM':36,'RDMSOL':37}
# 读取模型参数
weather_data = ExcelWeatherDataProvider(os.path.join(weather_dir,'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                                                            format(st_loc(row['lat']), st_loc(row['lon']))))
crop_name = row['crop_name_winter']  #作物名称
variety_name = row['variety_name_winter']  #作物种类名称
cropdata.set_active_crop(crop_name, variety_name)
soildata = CABOFileReader(os.path.join(soil_parameter_dir,'ec3.new'))  # 土壤文件

sitedata = {'SSMAX'  : 0.,
            'IFUNRN' : 0,
            'NOTINF' : 0,
            'SSI'    : 0,
            'WAV'    : 30,
            'SMLIM'  : 0.03,
            'RDMSOL'  : 120,
            'CO2' : 360,
            'NAVAILI': 10,
            'PAVAILI': 10,
            'KAVAILI': 10,
            'NSOILBASE':10,
            'PSOILBASE':10,
            'KSOILBASE':10,
            'BG_N_SUPPLY': 0.091,
            'BG_K_SUPPLY': 0.091,
            'BG_P_SUPPLY': 0.091,
            'NSOILBASE_FR':0.025,
            'PSOILBASE_FR':0.025,
            'KSOILBASE_FR':0.025}
parameters = ParameterProvider(cropdata=cropdata, soildata=soildata, sitedata=sitedata)

#创建文档储存模型输出结果
with open(os.path.join(para_dir,'result.txt'),'a') as fp2:
    fp2.writelines(['1','\n','TSWO','\n','time = no','\n'])
    #打开simlab输出的文档
    with open(os.path.join(para_dir,'EFASTDOC3250_50.SAM'),'r') as fp:
        fp.readline() # 第一行
        number = fp.readline() #第二行为生成参数个数
        fp.readline() #变量个数
        fp.readline() #0  此后开始读参数
        fp2.write(str(number))
        for i in range(int(number)):
            sim_paraments = list(map(float,fp.readline().split('\t')[:-1]))
            # 更改参数
            for iterm,value in change_data.items():
                parameters[iterm] = sim_paraments[value]
            parameters['SLATB'][1]=sim_paraments[5]
            parameters['SLATB'][3]=sim_paraments[6]
            parameters['SLATB'][5]=sim_paraments[7]
            parameters['KDIFTB'][1]=sim_paraments[10]
            parameters['KDIFTB'][3]=sim_paraments[10]
            parameters['EFFTB'][1]=sim_paraments[40]
            parameters['EFFTB'][3]=sim_paraments[40]
            parameters['AMAXTB'][1]=sim_paraments[11]
            parameters['AMAXTB'][3]=sim_paraments[12]
            parameters['AMAXTB'][5]=sim_paraments[13]
            parameters['AMAXTB'][7]=sim_paraments[14]
            parameters['AMAXTB'][1]=sim_paraments[11]
            parameters['RDRRTB'][5]=sim_paraments[25]
            parameters['RDRRTB'][7]=sim_paraments[25]
            parameters['RDRSTB'][5]=sim_paraments[26]
            agromanagement = YAMLAgroManagementReader(os.path.join(data_dir,'wheat{}.agro'.format(int(sim_paraments[39]))))
            agromanagement[0][datetime.date(2019, 10, 1)]['CropCalendar']['crop_start_date']=sow_date[round(sim_paraments[38])]
            wf = Wofost80_NWLP_FD_beta(parameters, weatherdataprovider, agromanagement)
            wf.run_till_terminate()
            output = wf.get_summary_output()
            fp2.write(str(output[0]['TWSO']))
            fp2.write('\n')
            if i%100==0:
                print(i)
end=datetime.datetime.now()
print('运行完成,共用时{}'.format(end-start))
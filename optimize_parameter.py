import os
import datetime
import pandas as pd
import numpy as np
import nlopt
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
from pcse.models import Wofost80_PP_beta
# 导入通用的实用工具函数
from utils import st_loc  # 规范化经纬度至0.5°
from utils import argo_w_modify  # 修改施肥灌溉等管理参数
from utils import argo_r_modify  # 修改施肥灌溉等管理参数
from utils import set_site_data  # 设置站点数据


class ModelRerunner(object):
    """Reruns a given model with different values of parameters TWDI and SPAN.
    Returns a pandas DataFrame with simulation results of the model with given
    parameter values.
    """
    # parameters to calibrate: EFFTB40 CVS
    def __init__(self, params, wdp, agro):
        self.params = params
        self.wdp = wdp
        self.agro = agro

    def __call__(self, par_values):
        # Check if correct number of parameter values were provided
        #         if len(par_values) != len(self.parameters):
        #             msg = "Optimizing %i parameters, but only % values were provided!" % (len(self.parameters, len(par_values)))
        #             raise RuntimeError(msg)
        #         # Clear any existing overrides
        #         self.params.clear_override()
        # Set overrides for the new parameter values
        self.params['SPAN'] = par_values[0]
        self.params['KDIFTB'][1] = par_values[1]
        self.params['KDIFTB'][3] = par_values[2]
        self.params['EFFTB'][1] = par_values[3]
        self.params['EFFTB'][3] = par_values[4]
        self.params['AMAXTB'][1] = par_values[5]
        self.params['AMAXTB'][3] = par_values[6]
        self.params['AMAXTB'][5] = par_values[7]
        self.params['CVS'] = par_values[8]
        self.params['CVO'] = par_values[9]
        self.params['CVL'] = par_values[10]
        self.params['CVR'] = par_values[11]
        # 数据替换
        self.params['TDWI'] = sub_data.loc[sub_data['品种'] == variety, ['播量（计算）']].iloc[0, 0]  # 播量
        self.params['SMW'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[0]  # 萎蔫点
        self.params['SMFCF'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[1]  # 田间持水量
        self.params['SM0'] = soil_data(SAND, CLAY, OM, BULK_DENSITY)[2]  # 饱和含水量

    # Run the model with given parameter values
    wofost = Wofost71_WLP_FD(self.params, self.wdp, self.agro)
    wofost.run_till_terminate()
    df = pd.DataFrame(wofost.get_output()).set_index("day")
    return df


class ObjectiveFunctionCalculator(object):
    """Computes the objective function.

    This class runs the simulation model with given parameter values and returns the objective
    function as the sum of squared difference between observed and simulated LAI.
.   """

    def __init__(self, params, wdp, agro, observations):
        self.modelrerunner = ModelRerunner(params, wdp, agro)
        self.df_observations = observations
        self.n_calls = 0

    def __call__(self, par_values, grad=None):
        """Runs the model and computes the objective function for given par_values.

        The input parameter 'grad' must be defined in the function call, but is only
        required for optimization methods where analytical gradients can be computed.
        """
        self.n_calls += 1
        print(".", end="")
        # Run the model and collect output
        self.df_simulations = self.modelrerunner(par_values)
        # compute the differences by subtracting the DataFrames
        # Note that the dataframes automatically join on the index (dates) and column names
        df_differences_tagp = self.df_observations['生物量kg/ha'] - self.df_simulations['TAGP']
        df_differences_twso = self.df_observations['穗生物量kg/ha'] - self.df_simulations['TWSO']
        df_differences_lai = self.df_observations['LAI'] - self.df_simulations['LAI']
        # Compute the RMSE on the LAI column
        obj_func = (np.sqrt(np.mean(df_differences_tagp ** 2)) / abs(np.mean(df_differences_tagp)) +
                    np.sqrt(np.mean(df_differences_twso ** 2)) / abs(np.mean(df_differences_twso)) +
                    np.sqrt(np.mean(df_differences_lai ** 2)) / abs(np.mean(df_differences_lai)))
        return obj_func


def optimize_wheat():
    data_dir = r'D:\\Desktop\\WOFOST_AP\\workspace'  # 工作路径
    weather_dir = r'D:\Desktop\WOFOST_AP\parameters\meteorological_parameter'  # 气象数据路径
    crop_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\crop_parameter'  # 作物文件路径
    soil_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\soil_parameter'  # 土壤文件路径
    management_parameter_dir = r'D:\Desktop\WOFOST_AP\parameters\management_parameter'  # 管理文件路径
    data_base_info = pd.read_excel(os.path.join(data_dir, 'sample_point_test0110.xlsx'), sheet_name='Sheet1')  # 模拟的位置
    row = data_base_info.loc[0]
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


if __name__ == "__main__":
    optimize_wheat()
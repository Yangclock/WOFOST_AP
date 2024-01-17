import os
import pandas as pd
import numpy as np
import nlopt
import matplotlib.pyplot as plt
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
from utils import argo_r_modify  # 修改施肥灌溉等管理参数
from utils import set_site_data  # 设置站点数据
from utils import sg_envelope_filter  # sg滤波


class ModelRerunnerWheat(object):
    """
    以不同的输入值重新运行模型
    Returns dataframe格式的模拟结果
    """

    def __init__(self, params, wdp, agro):
        self.params = params
        self.wdp = wdp
        self.agro = agro

    def __call__(self, par_values):
        self.params['TSUM1'] = par_values[0]
        self.params['TSUM2'] = par_values[1]
        self.params['TDWI'] = par_values[2]
        self.params['SLATB'][1] = par_values[3]
        self.params['SLATB'][3] = par_values[4]
        self.params['AMAXTB'][1] = par_values[5]
        self.params['SPAN'] = par_values[6]
        self.params['KDIFTB'][1] = par_values[7]
        self.params['FRTB'][1] = par_values[8]
        self.params['FRTB'][9] = par_values[9]
        self.params['FLTB'][1] = par_values[10]
        self.params['FSTB'][1] = 1 - par_values[10]
        self.params['RMR'] = par_values[11]
        # Run the model with given parameter values
        wofost = Wofost80_NWLP_FD_beta(self.params, self.wdp, self.agro)
        wofost.run_till_terminate()
        df = pd.DataFrame(wofost.get_output()).set_index("day")
        return df


class ModelRerunnerRice1(object):
    """
    以不同的输入值重新运行模型
    Returns dataframe格式的模拟结果
    """

    def __init__(self, params, wdp, agro):
        self.params = params
        self.wdp = wdp
        self.agro = agro

    def __call__(self, par_values):
        self.params['TSUM1'] = par_values[0]
        self.params['TSUM2'] = par_values[1]
        self.params['SLATB'][3] = par_values[2]
        self.params['TBASE'] = par_values[3]
        self.params['KDIFTB'][7] = par_values[4]
        self.params['EFFTB'][1] = par_values[5]
        self.params['CVL'] = par_values[6]
        self.params['CVO'] = par_values[7]
        self.params['RMO'] = par_values[8]
        self.params['RMS'] = par_values[9]
        self.params['FRTB'][7] = par_values[10]
        self.params['FLTB'][3] = par_values[11]
        self.params['FLTB'][5] = par_values[12]
        self.params['FSTB'][3] = 1 - par_values[11]
        self.params['FSTB'][5] = 1 - par_values[12]
        self.params['RDI'] = par_values[13]
        # Run the model with given parameter values
        wofost = Wofost80_NWLP_FD_beta(self.params, self.wdp, self.agro)
        wofost.run_till_terminate()
        df = pd.DataFrame(wofost.get_output()).set_index("day")
        return df


class ModelRerunnerRice2(object):
    """
    以不同的输入值重新运行模型
    Returns dataframe格式的模拟结果
    """

    def __init__(self, params, wdp, agro):
        self.params = params
        self.wdp = wdp
        self.agro = agro

    def __call__(self, par_values):
        self.params['TSUM1'] = par_values[0]
        self.params['TSUM2'] = par_values[1]
        self.params['SLATB'][3] = par_values[2]
        self.params['TBASE'] = par_values[3]
        self.params['EFFTB'][1] = par_values[4]
        self.params['EFFTB'][3] = par_values[5]
        self.params['AMAXTB'][1] = par_values[6]
        self.params['CVL'] = par_values[7]
        self.params['FRTB'][3] = par_values[8]
        self.params['FRTB'][5] = par_values[9]
        self.params['FLTB'][3] = par_values[10]
        self.params['FLTB'][5] = par_values[11]
        self.params['FLTB'][7] = par_values[12]
        self.params['FSTB'][3] = 1 - par_values[10]
        self.params['FSTB'][5] = 1 - par_values[11]
        self.params['FSTB'][7] = 1 - par_values[12]
        self.params['RDRSTB'][5] = par_values[12]
        # Run the model with given parameter values
        wofost = Wofost80_NWLP_FD_beta(self.params, self.wdp, self.agro)
        wofost.run_till_terminate()
        df = pd.DataFrame(wofost.get_output()).set_index("day")
        return df


class ObjectiveFunctionCalculatorWheat(object):
    """
    计算代价函数
    """

    def __init__(self, params, wdp, agro, observations):
        self.modelrerunner = ModelRerunnerWheat(params, wdp, agro)
        self.df_observations = observations
        self.n_calls = 0

    def __call__(self, par_values, grad=None):
        """
        运行模型并计算目标函数
        输入参数 'grad' 必须在函数调用中定义，但只是计算解析梯度的优化方法所需的
        """
        self.n_calls += 1
        print(".", end="")
        # 根据输入参数运行模型
        self.df_simulations = self.modelrerunner(par_values)
        # 通过减去 DataFrame 来计算差异
        # 请注意，数据帧自动连接索引（日期）和列名
        df_differences_lai = self.df_observations['LAI'] - self.df_simulations['LAI']
        # 计算模拟LAI的 代价函数（均方根百分比误差）
        obj_func = np.sqrt(np.mean(df_differences_lai ** 2))
        return obj_func


class ObjectiveFunctionCalculatorRice1(object):
    """
    计算代价函数
    """

    def __init__(self, params, wdp, agro, observations):
        self.modelrerunner = ModelRerunnerRice1(params, wdp, agro)
        self.df_observations = observations
        self.n_calls = 0

    def __call__(self, par_values, grad=None):
        """
        运行模型并计算目标函数
        输入参数 'grad' 必须在函数调用中定义，但只是计算解析梯度的优化方法所需的
        """
        self.n_calls += 1
        print(".", end="")
        # 根据输入参数运行模型
        self.df_simulations = self.modelrerunner(par_values)
        # 通过减去 DataFrame 来计算差异
        # 请注意，数据帧自动连接索引（日期）和列名
        df_differences_lai = self.df_observations['LAI'] - self.df_simulations['LAI']
        # 计算模拟LAI的 代价函数（均方根百分比误差）
        obj_func = np.sqrt(np.mean(df_differences_lai ** 2))
        return obj_func


class ObjectiveFunctionCalculatorRice2(object):
    """
    计算代价函数
    """

    def __init__(self, params, wdp, agro, observations):
        self.modelrerunner = ModelRerunnerRice2(params, wdp, agro)
        self.df_observations = observations
        self.n_calls = 0

    def __call__(self, par_values, grad=None):
        """
        运行模型并计算目标函数
        输入参数 'grad' 必须在函数调用中定义，但只是计算解析梯度的优化方法所需的
        """
        self.n_calls += 1
        print(".", end="")
        # 根据输入参数运行模型
        self.df_simulations = self.modelrerunner(par_values)
        # 通过减去 DataFrame 来计算差异
        # 请注意，数据帧自动连接索引（日期）和列名
        df_differences_lai = self.df_observations['LAI'] - self.df_simulations['LAI']
        # 计算模拟LAI的 代价函数（均方根百分比误差）
        obj_func = np.sqrt(np.mean(df_differences_lai ** 2))
        return obj_func


def optimize_wheat():
    # 路径设置
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "model_parameter_optimize")  # 工作路径
    weather_dir = os.path.join(work_dir, "parameters", "meteorological_parameter")  # 气象数据路径
    crop_parameter_dir = os.path.join(work_dir, "parameters", "crop_parameter")  # 作物文件路径
    soil_parameter_dir = os.path.join(work_dir, "parameters", "soil_parameter")  # 土壤文件路径
    management_parameter_dir = os.path.join(work_dir, "parameters", "management_parameter")  # 管理文件路径
    # 初始化模型参数
    data_base_info = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet1')  # 模拟的位置
    row = data_base_info.loc[2]
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
    # 导入观测数据
    lai_modis = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet4')  # modis作为观测值
    lai_ob = sg_envelope_filter(lai_modis.iloc[:, 1], 3, 0.06, 1)
    lai_ob_df = pd.DataFrame(lai_ob, index=lai_modis.iloc[:, 0])
    lai_ob_df.columns = ["LAI"]

    TSUM1_range = [800, 1200]
    TSUM2_range = [600, 1000]
    TDWI_range = [100, 220]
    SLATB1_range = [0.0012, 0.00212]
    SLATB3_range = [0.0012, 0.00212]
    AMAXTB1_range = [30, 36]
    SPAN_range = [21, 41]
    KDIFTB1_range = [0.4, 0.8]
    FRTB1_range = [0.4, 0.6]
    FRTB9_range = [0.27, 0.33]
    FLTB1_range = [0.6, 0.7]
    RMR_range = [0.01, 0.02]

    objfunc_calculator = ObjectiveFunctionCalculatorWheat(parameters, weather_data, agromanagement, lai_ob_df)
    opt = nlopt.opt(nlopt.LN_SBPLX, 12)
    opt.set_min_objective(objfunc_calculator)
    opt.set_lower_bounds(
        [TSUM1_range[0], TSUM2_range[0], TDWI_range[0], SLATB1_range[0], SLATB3_range[0], AMAXTB1_range[0],
         SPAN_range[0], KDIFTB1_range[0], FRTB1_range[0], FRTB9_range[0], FLTB1_range[0], RMR_range[0]])
    opt.set_upper_bounds(
        [TSUM1_range[1], TSUM2_range[1], TDWI_range[1], SLATB1_range[1], SLATB3_range[1], AMAXTB1_range[1],
         SPAN_range[1], KDIFTB1_range[1], FRTB1_range[1], FRTB9_range[1], FLTB1_range[1], RMR_range[1]])
    opt.set_initial_step([20, 20, 6, 0.000046, 0.000046, 0.3, 1, 0.02, 0.01, 0.003, 0.005, 0.0005])
    opt.set_maxeval(3000)
    opt.set_ftol_rel(0.5)
    firstguess = [960, 850, 150, 0.0015, 0.0015, 32, 28, 0.6, 0.45, 0.27, 0.6, 0.015]
    x = opt.optimize(firstguess)
    print("\noptimum at TSUM1: %s, TSUM2: %s, TDWI: %s, SLATB1: %s, SLATB3: %s, AMAXTB1: %s"
          ", SPAN: %s, KDIFTB1: %s, FRTB1: %s, FRTB9: %s, FLTB1: %s, RMR: %s" %
          (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10], x[11]))
    print("minimum value = ", opt.last_optimum_value())
    print("result code = ", opt.last_optimize_result())
    print("With %i function calls" % objfunc_calculator.n_calls)

    error = objfunc_calculator(x)
    fig, axes = plt.subplots(figsize=(12, 8))
    axes.plot_date(lai_ob_df.index, lai_ob_df.LAI, label="MODIS LAI")
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "k:",
                   label="optimized")
    error = objfunc_calculator(firstguess)
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "g:",
                   label="first guess")
    axes.set_title("MODIS LAI observations with optimized model")
    fig.legend()
    plt.show()


def optimize_rice1():
    # 路径设置
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "model_parameter_optimize")  # 工作路径
    weather_dir = os.path.join(work_dir, "parameters", "meteorological_parameter")  # 气象数据路径
    crop_parameter_dir = os.path.join(work_dir, "parameters", "crop_parameter")  # 作物文件路径
    soil_parameter_dir = os.path.join(work_dir, "parameters", "soil_parameter")  # 土壤文件路径
    management_parameter_dir = os.path.join(work_dir, "parameters", "management_parameter")  # 管理文件路径
    # 初始化模型参数
    data_base_info = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet1')  # 模拟的位置
    row = data_base_info.loc[0]
    crop_name = row['crop_name_summer']  # 作物名称
    variety_name = row['variety_name_summer']  # 作物种类名称
    crop_data = YAMLCropDataProvider(crop_parameter_dir)  # 作物参数读取
    crop_data.set_active_crop(crop_name, variety_name)  # 设置当前活动作物
    soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file'] + '.new'))  # 土壤参数读取
    parameters = ParameterProvider(crop_data, soil_data,
                                   set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 上述参数与站点参数打包
    agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo_r1.yaml')),
                                   row)  # 管理参数读取
    weather_data = ExcelWeatherDataProvider(
        os.path.join(weather_dir, 'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                     format(st_loc(row['lat']), st_loc(row['lon']))))
    # 导入观测数据
    lai_modis = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet2')  # modis作为观测值
    lai_ob = sg_envelope_filter(lai_modis.iloc[:, 1], 3, 0.5, 1)
    lai_ob_df = pd.DataFrame(lai_ob, index=lai_modis.iloc[:, 0])
    lai_ob_df.columns = ["LAI"]

    TSUM1_range = [1500, 1800]
    TSUM2_range = [500, 800]
    SLATB3_range = [0.005, 0.01]
    TBASE_range = [6, 12]
    KDIFTB7_range = [0.5, 0.8]
    EFFTB1_range = [0.5, 0.6]
    CVL_range = [0.6, 0.8]
    CVO_range = [0.6, 0.8]
    RMO_range = [0.001, 0.005]
    RMS_range = [0.01, 0.03]
    FRTB7_range = [0.4, 0.6]
    FLTB3_range = [0.5, 0.7]
    FLTB5_range = [0.2, 0.4]
    RDI_range = [6, 20]

    objfunc_calculator = ObjectiveFunctionCalculatorRice1(parameters, weather_data, agromanagement, lai_ob_df)
    # Start optimizer with the SUBPLEX algorithm for two parameters
    opt = nlopt.opt(nlopt.LN_SBPLX, 14)
    # Assign the objective function calculator
    opt.set_min_objective(objfunc_calculator)
    # lower bounds of parameters values
    opt.set_lower_bounds(
        [TSUM1_range[0], TSUM2_range[0], SLATB3_range[0], TBASE_range[0], KDIFTB7_range[0], EFFTB1_range[0],
         CVL_range[0], CVO_range[0], RMO_range[0], RMS_range[0], FRTB7_range[0], FLTB3_range[0], FLTB5_range[0],
         RDI_range[0]])
    # upper bounds of parameters values
    opt.set_upper_bounds(
        [TSUM1_range[1], TSUM2_range[1], SLATB3_range[1], TBASE_range[1], KDIFTB7_range[1], EFFTB1_range[1],
         CVL_range[1], CVO_range[1], RMO_range[1], RMS_range[1], FRTB7_range[1], FLTB3_range[1], FLTB5_range[1],
         RDI_range[1]])
    # the initial step size to compute numerical gradients
    opt.set_initial_step([15, 15, 0.00025, 0.3, 0.015, 0.015, 0.01, 0.01, 0.0002, 0.001, 0.01, 0.001, 0.001, 0.7])
    # Maximum number of evaluations allowed
    opt.set_maxeval(3000)
    # Relative tolerance for convergence
    opt.set_ftol_rel(0.5)

    # Start the optimization with the first guess
    firstguess = [1600, 700, 0.0075, 8, 0.6, 0.54, 0.754, 0.684, 0.003, 0.02, 0.5, 0.57, 0.35, 10]
    x = opt.optimize(firstguess)
    print("\noptimum at TSUM1: %s, TSUM2: %s, SLATB3: %s, TBASE: %s, KDIFTB7: %s, EFFTB1: %s"
          ", CVL: %s, CVO: %s, RMO: %s, RMS: %s, FRTB7: %s, FLTB3: %s, FLTB5: %s, RDI: %s" %
          (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10], x[11], x[12], x[13]))
    print("minimum value = ", opt.last_optimum_value())
    print("result code = ", opt.last_optimize_result())
    print("With %i function calls" % objfunc_calculator.n_calls)

    # rerun with the best parameters found
    error = objfunc_calculator(x)
    fig, axes = plt.subplots(figsize=(12, 8))
    axes.plot_date(lai_ob_df.index, lai_ob_df.LAI, label="MODIS LAI")
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "k:",
                   label="optimized")
    # rerun to show the first guess for the first guess
    error = objfunc_calculator(firstguess)
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "g:",
                   label="first guess")
    axes.set_title("MODIS LAI observations with optimized model")
    fig.legend()
    plt.show()


def optimize_rice2():
    # 路径设置
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "model_parameter_optimize")  # 工作路径
    weather_dir = os.path.join(work_dir, "parameters", "meteorological_parameter")  # 气象数据路径
    crop_parameter_dir = os.path.join(work_dir, "parameters", "crop_parameter")  # 作物文件路径
    soil_parameter_dir = os.path.join(work_dir, "parameters", "soil_parameter")  # 土壤文件路径
    management_parameter_dir = os.path.join(work_dir, "parameters", "management_parameter")  # 管理文件路径
    # 初始化模型参数
    data_base_info = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet1')  # 模拟的位置
    row = data_base_info.loc[1]
    crop_name = row['crop_name_summer']  # 作物名称
    variety_name = row['variety_name_summer']  # 作物种类名称
    crop_data = YAMLCropDataProvider(crop_parameter_dir)  # 作物参数读取
    crop_data.set_active_crop(crop_name, variety_name)  # 设置当前活动作物
    soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file'] + '.new'))  # 土壤参数读取
    parameters = ParameterProvider(crop_data, soil_data,
                                   set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 上述参数与站点参数打包
    agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo_r2.yaml')),
                                   row)  # 管理参数读取
    weather_data = ExcelWeatherDataProvider(
        os.path.join(weather_dir, 'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                     format(st_loc(row['lat']), st_loc(row['lon']))))
    # 导入观测数据
    lai_modis = pd.read_excel(os.path.join(data_dir, 'LAI.xlsx'), sheet_name='Sheet3')  # modis作为观测值
    lai_ob = sg_envelope_filter(lai_modis.iloc[:, 1], 3, 0.5, 1)
    lai_ob_df = pd.DataFrame(lai_ob, index=lai_modis.iloc[:, 0])
    lai_ob_df.columns = ["LAI"]
    # 设置变量范围
    TSUM1_range = [1400, 1800]
    TSUM2_range = [400, 600]
    SLATB3_range = [0.0024, 0.0036]
    TBASE_range = [6, 12]
    EFFTB1_range = [0.4, 0.6]
    EFFTB3_range = [0.3, 0.5]
    AMAXTB1_range = [30, 44]
    CVL_range = [0.65, 0.85]
    FRTB3_range = [0.4, 0.5]
    FRTB5_range = [0.3, 0.4]
    FLTB3_range = [0.57, 0.67]
    FLTB5_range = [0.5, 0.62]
    FLTB7_range = [0.5, 0.62]
    RDRSTB5_range = [0.01, 0.03]

    objfunc_calculator = ObjectiveFunctionCalculatorRice2(parameters, weather_data, agromanagement, lai_ob_df)
    opt = nlopt.opt(nlopt.LN_SBPLX, 14)  # 设定优化参数数量
    opt.set_min_objective(objfunc_calculator)
    opt.set_lower_bounds(  # 设置参数最小值
        [TSUM1_range[0], TSUM2_range[0], SLATB3_range[0], TBASE_range[0], EFFTB1_range[0], EFFTB3_range[0],
         AMAXTB1_range[0], CVL_range[0], FRTB3_range[0], FRTB5_range[0], FLTB3_range[0], FLTB5_range[0],
         FLTB7_range[0], RDRSTB5_range[0]])
    opt.set_upper_bounds(  # 设置参数最大值
        [TSUM1_range[1], TSUM2_range[1], SLATB3_range[1], TBASE_range[1], EFFTB1_range[1], EFFTB3_range[1],
         AMAXTB1_range[1], CVL_range[1], FRTB3_range[1], FRTB5_range[1], FLTB3_range[1], FLTB5_range[1],
         FLTB7_range[1], RDRSTB5_range[1]])
    # the initial step size to compute numerical gradients
    opt.set_initial_step([20, 10, 0.00006, 0.3, 0.01, 0.01, 0.7, 0.01, 0.005, 0.005, 0.005, 0.006, 0.006, 0.001])
    # Maximum number of evaluations allowed
    opt.set_maxeval(3000)
    # Relative tolerance for convergence
    opt.set_ftol_rel(0.5)
    # Start the optimization with the first guess
    firstguess = [1630, 530, 0.003, 8, 0.54, 0.36, 40, 0.754, 0.45, 0.35, 0.62, 0.57, 0.57, 0.02]
    x = opt.optimize(firstguess)
    print("\noptimum at TSUM1: %s, TSUM2: %s, SLATB3: %s, TBASE: %s, EFFTB1: %s, EFFTB3: %s"
          ", AMAXTB1: %s, CVL: %s, FRTB3: %s, FRTB5: %s, FLTB3: %s, FLTB5: %s, FLTB7: %s, RDRSTB5: %s" %
          (x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7], x[8], x[9], x[10], x[11], x[12], x[13]))
    print("minimum value = ", opt.last_optimum_value())
    print("result code = ", opt.last_optimize_result())
    print("With %i function calls" % objfunc_calculator.n_calls)

    # rerun with the best parameters found
    error = objfunc_calculator(x)
    fig, axes = plt.subplots(figsize=(12, 8))
    axes.plot_date(lai_ob_df.index, lai_ob_df.LAI, label="MODIS LAI")
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "k:",
                   label="optimized")
    # rerun to show the first guess for the first guess
    error = objfunc_calculator(firstguess)
    axes.plot_date(objfunc_calculator.df_simulations.index, objfunc_calculator.df_simulations.LAI, "g:",
                   label="first guess")
    axes.set_title("MODIS LAI observations with optimized model")
    fig.legend()
    plt.show()


if __name__ == "__main__":
    optimize_rice2()

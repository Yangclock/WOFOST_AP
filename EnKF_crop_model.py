import datetime
import os
import copy
import pandas as pd
import numpy as np
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
from utils import jd_to_time  # 转换儒略日


def enkf():
    # 路径设置
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "workspace")  # 工作路径
    re_dir = os.path.join(data_dir, "result")
    weather_dir = os.path.join(work_dir, "parameters", "meteorological_parameter")  # 气象数据路径
    crop_parameter_dir = os.path.join(work_dir, "parameters", "crop_parameter")  # 作物文件路径
    soil_parameter_dir = os.path.join(work_dir, "parameters", "soil_parameter")  # 土壤文件路径
    management_parameter_dir = os.path.join(work_dir, "parameters", "management_parameter")  # 管理文件路径
    ensemble_size = 50  # 设置集合大小
    np.random.seed(10000)  # 设置随机数的种子以便获得相同的结果
# --------------------------------------------------------
#                     WOFOST运行
# --------------------------------------------------------
    data_base_info = pd.read_excel(os.path.join(data_dir, 'sample_point.xlsx'), sheet_name='Sheet1')
    # 汇总所有样点结果，win_TWSO、win_TAGP、win_RPTAKE、sum_TWSO、sum_TAGP、sum_RPTAKE、PAVAIL
    ap_summary_output = pd.DataFrame(
        columns=["BSM", "win_TWSO", "win_TAGP", "win_RPUPTAKE", "sum_TWSO", "sum_TAGP", "sum_RPUPTAKE", "PAVAIL"],
        index=data_base_info.index)
    ap_summary_output["BSM"] = data_base_info["标识码"]
    try:
        for index, row in data_base_info.iterrows():  # 逐行读取点位信息并模拟
            row_output = pd.DataFrame(
                columns=["BSM", "win_TAGP", "win_TWSO", "win_RPUPTAKE", "sum_TAGP", "sum_TWSO", "sum_RPUPTAKE", "PAVAIL"],
                index=[index])
            row_output["BSM"] = row["标识码"]
            crop_name_winter = row['crop_name_winter']  # 作物名称
            variety_name_winter = row['variety_name_winter']  # 作物种类名称
            crop_data = YAMLCropDataProvider(crop_parameter_dir)  # 作物参数读取
            soil_data = CABOFileReader(os.path.join(soil_parameter_dir, row['soil_file'] + '.new'))  # 土壤参数读取
            weather_data = ExcelWeatherDataProvider(
                os.path.join(weather_dir, 'NASA天气文件lat={0:.1f},lon={1:.1f}.xlsx'.  # 气象参数
                             format(st_loc(row['lat']), st_loc(row['lon']))))
            # 夏收作物模拟
            if crop_name_winter == 'wheat_local':
                crop_data.set_active_crop(crop_name_winter, variety_name_winter)  # 设置当前活动作物
                parameters = ParameterProvider(crop_data, soil_data,
                                               set_site_data(row['NAVAILI'], row['PAVAILI'], row['KAVAILI']))  # 参数打包
                agromanagement = argo_w_modify(
                    YAMLAgroManagementReader(os.path.join(management_parameter_dir, 'argo_w.yaml')),
                    row)  # 管理参数读取
                # 添加观测数据
                variables_for_DA = ["LAI"]
                dates_of_observation = row[38:55].index.tolist()
                observed_lai = np.array(row[38:55])
                std_lai = observed_lai * 0.2  # MODIS LAI的不确定性大概有20%
                observations_for_DA = [(d, {"LAI": (lai, errlai)}) for d, lai, errlai in
                                       zip(dates_of_observation, observed_lai, std_lai)]
                # 定义集合中的变异性
                override_parameters = {"CROPTIME": np.random.normal(290., 5., ensemble_size),
                                       "TDWI": np.random.normal(200., 40., ensemble_size),
                                       "SLATB1": np.random.normal(0.0015, 0.0005, ensemble_size),
                                       "SPAN": np.random.normal(30., 5., ensemble_size),
                                       "FLTB1": np.random.normal(0.65, 0.025, ensemble_size)}
                # 初始化整体
                ensemble = []
                for i in range(ensemble_size):
                    p = copy.deepcopy(parameters)
                    a = copy.deepcopy(agromanagement)
                    p["TDWI"] = override_parameters["TDWI"][i]
                    p["SLATB"][1] = override_parameters["SLATB1"][i]
                    p["SPAN"] = override_parameters["SPAN"][i]
                    p["FLTB"][1] = override_parameters["FLTB1"][i]
                    p["FSTB"][1] = 1 - override_parameters["FLTB1"][i]
                    sow_date = jd_to_time(round(override_parameters["CROPTIME"][i]))
                    if sow_date < datetime.date(2019,10,1):
                        sow_date = datetime.date(2019,10,1)
                    a[0][datetime.date(2019, 10, 1)]['CropCalendar']['crop_start_date'] = sow_date
                    member = Wofost80_NWLP_FD_beta(p, weather_data, a)
                    ensemble.append(member)
                # 实现数据同化本身
                for all_ob_LAI in range(len(observations_for_DA)):
                    day, obs = observations_for_DA.pop(0)
                    print(".", end="")
                    for member in ensemble:
                        member.run_till(day)
                    collected_states = []
                    for member in ensemble:
                        t = {}
                        for state in variables_for_DA:
                            t[state] = member.get_variable(state)
                        collected_states.append(t)
                    df_A = pd.DataFrame(collected_states)  #
                    A = np.matrix(df_A).T  # 矩阵A用于运算
                    P_e = np.matrix(df_A.cov())  # 为了计算卡尔曼增益，我们需要计算系综内模拟状态的（协）方差矩阵
                    # 计算扰动观测值及其均值和协方差
                    perturbed_obs = []
                    for state in variables_for_DA:
                        (value, std) = obs[state]
                        d = np.random.normal(value, std, (ensemble_size))
                        perturbed_obs.append(d)
                    df_perturbed_obs = pd.DataFrame(perturbed_obs).T
                    df_perturbed_obs.columns = variables_for_DA
                    D = np.matrix(df_perturbed_obs).T
                    R_e = np.matrix(df_perturbed_obs.cov())
                    # 卡尔曼滤波
                    H = np.identity(len(obs))
                    K1 = P_e * (H.T)
                    K2 = (H * P_e) * H.T
                    K = K1 * ((K2 + R_e).I)
                    Aa = A + K * (D - (H * A))
                    df_Aa = pd.DataFrame(Aa.T, columns=variables_for_DA)
                    for member, new_states in zip(ensemble, df_Aa.itertuples()):
                        r1 = member.set_variable("LAI", new_states.LAI)
                an_u, ap_u, ak_u, tagp, twso, pt = [], [], [], [], [], []
                for member in ensemble:
                    member.run_till_terminate()
                    output = pd.DataFrame(member.get_output()).set_index('day')  # 获取输出结果
                    summary_output = member.get_summary_output()
                    an_u.append(output["NAVAIL"].iloc[-1])
                    ap_u.append(output["PAVAIL"].iloc[-1])
                    ak_u.append(output["KAVAIL"].iloc[-1])
                    tagp.append(summary_output[0]["TAGP"])
                    twso.append(summary_output[0]["TWSO"])
                    pt.append(summary_output[0]["PuptakeTotal"])
                print(".")
                an, ap, ak = sum(an_u)/ensemble_size, sum(ap_u)/ensemble_size, sum(ak_u)/ensemble_size
                row_output["win_TAGP"], row_output["win_TWSO"], row_output["win_RPUPTAKE"], row_output["PAVAIL"] \
                    = sum(tagp)/ensemble_size, sum(twso)/ensemble_size, sum(pt)/ensemble_size, ap
            else:
                an, ap, ak = row['NAVAILI'], row['PAVAILI'], row['KAVAILI']
            # 秋收作物模拟
            crop_name_summer = row['crop_name_summer']  # 作物名称
            variety_name_summer = row['variety_name_summer']  # 作物种类名称
            if variety_name_summer == 'Hubei_rice_1':
                crop_data.set_active_crop(crop_name_summer, variety_name_summer)  # 设置当前活动作物
                parameters = ParameterProvider(crop_data, soil_data, set_site_data(an, ap, ak))  # 参数打包
                agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir,
                                                                                     'argo_r1.yaml')), row)  # 管理参数读取
                # 添加观测数据
                variables_for_DA = ["LAI"]
                dates_of_observation = row[55:62].index.tolist()
                observed_lai = np.array(row[55:62])
                std_lai = observed_lai * 0.2  # MODIS LAI的不确定性大概有20%
                observations_for_DA = [(d, {"LAI": (lai, errlai)}) for d, lai, errlai in
                                       zip(dates_of_observation, observed_lai, std_lai)]
                # 定义集合中的变异性
                override_parameters = {"CROPTIME": np.random.normal(171., 5., ensemble_size),
                                       "TSUM1": np.random.normal(1585., 50., ensemble_size),
                                       "SLATB3": np.random.normal(0.0074, 0.0005, ensemble_size),
                                       "EFFTB1": np.random.normal(0.5, 0.025, ensemble_size),
                                       "FRTB3": np.random.normal(0.2, 0.025, ensemble_size)}
                # 初始化整体
                ensemble = []
                for i in range(ensemble_size):
                    p = copy.deepcopy(parameters)
                    a = copy.deepcopy(agromanagement)
                    p["TSUM1"] = override_parameters["TSUM1"][i]
                    p["SLATB"][3] = override_parameters["SLATB3"][i]
                    p["EFFTB"][1] = override_parameters["EFFTB1"][i]
                    p["FRTB"][3] = override_parameters["FRTB3"][i]
                    sow_date = jd_to_time(round(override_parameters["CROPTIME"][i])).replace(year=2020)
                    if sow_date < datetime.date(2020,6,1):
                        sow_date = datetime.date(2020,6,1)
                    a[0][datetime.date(2020, 6, 1)]['CropCalendar']['crop_start_date'] = sow_date
                    member = Wofost80_NWLP_FD_beta(p, weather_data, a)
                    ensemble.append(member)
                # 实现数据同化本身
                for all_ob_LAI in range(len(observations_for_DA)):
                    day, obs = observations_for_DA.pop(0)
                    print(".", end="")
                    for member in ensemble:
                        member.run_till(day)
                    collected_states = []
                    for member in ensemble:
                        t = {}
                        for state in variables_for_DA:
                            t[state] = member.get_variable(state)
                        collected_states.append(t)
                    df_A = pd.DataFrame(collected_states)  #
                    A = np.matrix(df_A).T  # 矩阵A用于运算
                    P_e = np.matrix(df_A.cov())  # 为了计算卡尔曼增益，我们需要计算系综内模拟状态的（协）方差矩阵
                    # 计算扰动观测值及其均值和协方差
                    perturbed_obs = []
                    for state in variables_for_DA:
                        (value, std) = obs[state]
                        d = np.random.normal(value, std, (ensemble_size))
                        perturbed_obs.append(d)
                    df_perturbed_obs = pd.DataFrame(perturbed_obs).T
                    df_perturbed_obs.columns = variables_for_DA
                    D = np.matrix(df_perturbed_obs).T
                    R_e = np.matrix(df_perturbed_obs.cov())
                    # 卡尔曼滤波
                    H = np.identity(len(obs))
                    K1 = P_e * (H.T)
                    K2 = (H * P_e) * H.T
                    K = K1 * ((K2 + R_e).I)
                    Aa = A + K * (D - (H * A))
                    df_Aa = pd.DataFrame(Aa.T, columns=variables_for_DA)
                    for member, new_states in zip(ensemble, df_Aa.itertuples()):
                        r1 = member.set_variable("LAI", new_states.LAI)
                an_u, ap_u, ak_u, tagp, twso, pt = [], [], [], [], [], []
                for member in ensemble:
                    member.run_till_terminate()
                    output = pd.DataFrame(member.get_output()).set_index('day')  # 获取输出结果
                    summary_output = member.get_summary_output()
                    an_u.append(output["NAVAIL"].iloc[-1])
                    ap_u.append(output["PAVAIL"].iloc[-1])
                    ak_u.append(output["KAVAIL"].iloc[-1])
                    tagp.append(summary_output[0]["TAGP"])
                    twso.append(summary_output[0]["TWSO"])
                    pt.append(summary_output[0]["PuptakeTotal"])
                print(".")
                an, ap, ak = sum(an_u)/ensemble_size, sum(ap_u)/ensemble_size, sum(ak_u)/ensemble_size
                row_output["sum_TAGP"], row_output["sum_TWSO"], row_output["sum_RPUPTAKE"], row_output["PAVAIL"] \
                    = sum(tagp)/ensemble_size, sum(twso)/ensemble_size, sum(pt)/ensemble_size, ap
            if variety_name_summer == 'Hubei_rice_2':
                crop_data.set_active_crop(crop_name_summer, variety_name_summer)  # 设置当前活动作物
                parameters = ParameterProvider(crop_data, soil_data, set_site_data(an, ap, ak))  # 参数打包
                agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir,
                                                                                     'argo_r2.yaml')), row)  # 管理参数读取
                # 添加观测数据
                variables_for_DA = ["LAI"]
                dates_of_observation = row[55:62].index.tolist()
                observed_lai = np.array(row[55:62])
                std_lai = observed_lai * 0.2  # MODIS LAI的不确定性大概有20%
                observations_for_DA = [(d, {"LAI": (lai, errlai)}) for d, lai, errlai in
                                       zip(dates_of_observation, observed_lai, std_lai)]
                # 定义集合中的变异性
                override_parameters = {"CROPTIME": np.random.normal(191., 5., ensemble_size),
                                       "TSUM1": np.random.normal(1550., 50., ensemble_size),
                                       "SLATB3": np.random.normal(0.0032, 0.0005, ensemble_size),
                                       "EFFTB1": np.random.normal(0.6, 0.025, ensemble_size),
                                       "FRTB3": np.random.normal(0.4, 0.025, ensemble_size)}
                # 初始化整体
                ensemble = []
                for i in range(ensemble_size):
                    p = copy.deepcopy(parameters)
                    a = copy.deepcopy(agromanagement)
                    p["TSUM1"] = override_parameters["TSUM1"][i]
                    p["SLATB"][3] = override_parameters["SLATB3"][i]
                    p["EFFTB"][1] = override_parameters["EFFTB1"][i]
                    p["FRTB"][3] = override_parameters["FRTB3"][i]
                    sow_date = jd_to_time(round(override_parameters["CROPTIME"][i])).replace(year=2020)
                    a[0][datetime.date(2020, 6, 1)]['CropCalendar']['crop_start_date'] = sow_date
                    member = Wofost80_NWLP_FD_beta(p, weather_data, a)
                    ensemble.append(member)
                # 实现数据同化本身
                for all_ob_LAI in range(len(observations_for_DA)):
                    day, obs = observations_for_DA.pop(0)
                    print(".", end="")
                    for member in ensemble:
                        member.run_till(day)
                    collected_states = []
                    for member in ensemble:
                        t = {}
                        for state in variables_for_DA:
                            t[state] = member.get_variable(state)
                        collected_states.append(t)
                    df_A = pd.DataFrame(collected_states)  #
                    A = np.matrix(df_A).T  # 矩阵A用于运算
                    P_e = np.matrix(df_A.cov())  # 为了计算卡尔曼增益，我们需要计算系综内模拟状态的（协）方差矩阵
                    # 计算扰动观测值及其均值和协方差
                    perturbed_obs = []
                    for state in variables_for_DA:
                        (value, std) = obs[state]
                        d = np.random.normal(value, std, (ensemble_size))
                        perturbed_obs.append(d)
                    df_perturbed_obs = pd.DataFrame(perturbed_obs).T
                    df_perturbed_obs.columns = variables_for_DA
                    D = np.matrix(df_perturbed_obs).T
                    R_e = np.matrix(df_perturbed_obs.cov())
                    # 卡尔曼滤波
                    H = np.identity(len(obs))
                    K1 = P_e * (H.T)
                    K2 = (H * P_e) * H.T
                    K = K1 * ((K2 + R_e).I)
                    Aa = A + K * (D - (H * A))
                    df_Aa = pd.DataFrame(Aa.T, columns=variables_for_DA)
                    for member, new_states in zip(ensemble, df_Aa.itertuples()):
                        r1 = member.set_variable("LAI", new_states.LAI)
                an_u, ap_u, ak_u, tagp, twso, pt = [], [], [], [], [], []
                for member in ensemble:
                    member.run_till_terminate()
                    output = pd.DataFrame(member.get_output()).set_index('day')  # 获取输出结果
                    summary_output = member.get_summary_output()
                    an_u.append(output["NAVAIL"].iloc[-1])
                    ap_u.append(output["PAVAIL"].iloc[-1])
                    ak_u.append(output["KAVAIL"].iloc[-1])
                    tagp.append(summary_output[0]["TAGP"])
                    twso.append(summary_output[0]["TWSO"])
                    pt.append(summary_output[0]["PuptakeTotal"])
                print(".")
                an, ap, ak = sum(an_u)/ensemble_size, sum(ap_u)/ensemble_size, sum(ak_u)/ensemble_size
                row_output["sum_TAGP"], row_output["sum_TWSO"], row_output["sum_RPUPTAKE"], row_output["PAVAIL"] \
                    = sum(tagp)/ensemble_size, sum(twso)/ensemble_size, sum(pt)/ensemble_size, ap
            ap_summary_output.loc[index] = row_output.loc[index]
            print("\n已运行：%s" % index)
    except Exception:
        ap_summary_output.to_excel(os.path.join(re_dir, "EnKF最终结果暂存.xlsx"))
        print("\n出错前的结果已缓存")
    ap_summary_output.to_excel(os.path.join(re_dir, "EnKF多线程最终结果.xlsx"))


if __name__ == "__main__":
    enkf()

import os
import sys
import copy
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib
matplotlib.style.use("ggplot")
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
from pcse.models import Wofost80_PP_beta
# 导入通用的实用工具函数
from utils import st_loc  # 规范化经纬度至0.5°
from utils import argo_w_modify  # 修改施肥灌溉等管理参数
from utils import argo_r_modify  # 修改施肥灌溉等管理参数
from utils import set_site_data  # 设置站点数据


def enkf():
    # 路径设置
    work_dir = os.getcwd()
    data_dir = os.path.join(work_dir, "workspace")  # 工作路径
    re_dir = os.path.join(data_dir, "result")
    weather_dir = os.path.join(work_dir, "parameters", "meteorological_parameter")  # 气象数据路径
    crop_parameter_dir = os.path.join(work_dir, "parameters", "crop_parameter")  # 作物文件路径
    soil_parameter_dir = os.path.join(work_dir, "parameters", "soil_parameter")  # 土壤文件路径
    management_parameter_dir = os.path.join(work_dir, "parameters", "management_parameter")  # 管理文件路径
    # --------------------------------------------------------
    #                     WOFOST运行
    # --------------------------------------------------------
    data_base_info = pd.read_excel(os.path.join(data_dir, 'sample_point_test0116.xlsx'), sheet_name='Sheet1')
    # 汇总所有样点结果，win_TWSO、win_TAGP、win_RPTAKE、sum_TWSO、sum_TAGP、sum_RPTAKE、PAVAIL
    ap_summary_output = pd.DataFrame(
        columns=["BSM", "win_TWSO", "win_TAGP", "win_RPUPTAKE", "sum_TWSO", "sum_TAGP", "sum_RPUPTAKE", "PAVAIL"],
        index=data_base_info.index)
    ap_summary_output["BSM"] = data_base_info["标识码"]
    for index, row in data_base_info.iterrows():  # 逐行读取点位信息并模拟
        output_Flag = False
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
            wf = Wofost80_NWLP_FD_beta(parameters, weather_data, agromanagement)  # 定义模型
            wf.run_till_terminate()  # 运行模型直到终止
            #

            output = pd.DataFrame(wf.get_output()).set_index('day')  # 获取输出结果
            summary_output = wf.get_summary_output()
            AN, AP, AK = output["NAVAIL"].iloc[-1], output["PAVAIL"].iloc[-1], output["KAVAIL"].iloc[-1]
            row_output["win_TAGP"], row_output["win_TWSO"], row_output["win_RPUPTAKE"], row_output["PAVAIL"] \
                = summary_output[0]["TAGP"], summary_output[0]["TWSO"], summary_output[0]["PuptakeTotal"], AP
            file_name = 'wheat_result' + str(row["标识码"]) + '.xlsx'  # 输出excel表的文件名
            output.to_excel(os.path.join(re_dir, file_name))  # 将结果输出为excel表
            output_Flag = True
        else:
            AN, AP, AK = row['NAVAILI'], row['PAVAILI'], row['KAVAILI']
        # 秋收作物模拟
        crop_name_summer = row['crop_name_summer']  # 作物名称
        variety_name_summer = row['variety_name_summer']  # 作物种类名称
        if variety_name_summer == 'Hubei_rice_1':
            crop_data.set_active_crop(crop_name_summer, variety_name_summer)  # 设置当前活动作物
            parameters = ParameterProvider(crop_data, soil_data, set_site_data(AN, AP, AK))  # 参数打包
            agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir,
                                                                                 'argo_r1.yaml')), row)  # 管理参数读取
            wf = Wofost80_NWLP_FD_beta(parameters, weather_data, agromanagement)  # 定义模型
            wf.run_till_terminate()  # 运行模型直到终止
            output1 = pd.DataFrame(wf.get_output()).set_index('day')  # 获取输出结果
            summary_output = wf.get_summary_output()
            AP = output1["PAVAIL"].iloc[-1]
            row_output["sum_TAGP"], row_output["sum_TWSO"], row_output["sum_RPUPTAKE"], row_output["PAVAIL"] \
                = summary_output[0]["TAGP"], summary_output[0]["TWSO"], summary_output[0]["PuptakeTotal"], AP
            file_name = 'wheat_result' + str(row["标识码"]) + '.xlsx'  # 输出excel表的文件名
            if output_Flag:
                merge_output = pd.concat([output, output1], axis=0)
                merge_output.to_excel(os.path.join(re_dir, file_name))
            else:
                output.to_excel(os.path.join(re_dir, file_name))  # 将结果输出为excel表
        if variety_name_summer == 'Hubei_rice_2':
            crop_data.set_active_crop(crop_name_summer, variety_name_summer)  # 设置当前活动作物
            parameters = ParameterProvider(crop_data, soil_data, set_site_data(AN, AP, AK))  # 参数打包
            agromanagement = argo_r_modify(YAMLAgroManagementReader(os.path.join(management_parameter_dir,
                                                                                 'argo_r2.yaml')), row)  # 管理参数读取
            wf = Wofost80_NWLP_FD_beta(parameters, weather_data, agromanagement)  # 定义模型
            wf.run_till_terminate()  # 运行模型直到终止
            output1 = pd.DataFrame(wf.get_output()).set_index('day')  # 获取输出结果
            summary_output = wf.get_summary_output()
            AP = output1["PAVAIL"].iloc[-1]
            row_output["sum_TAGP"], row_output["sum_TWSO"], row_output["sum_RPUPTAKE"], row_output["PAVAIL"] \
                = summary_output[0]["TAGP"], summary_output[0]["TWSO"], summary_output[0]["PuptakeTotal"], AP
            file_name = 'wheat_result' + str(row["标识码"]) + '.xlsx'  # 输出excel表的文件名
            if output_Flag:
                merge_output = pd.concat([output, output1], axis=0)
                merge_output.to_excel(os.path.join(re_dir, file_name))
            else:
                output.to_excel(os.path.join(re_dir, file_name))  # 将结果输出为excel表
        ap_summary_output.loc[index] = row_output.loc[index]
    ap_summary_output.to_excel(os.path.join(re_dir, "最终结果.xlsx"))


if __name__ == "__main__":
    enkf()
import datetime
import math
import numpy as np


def time_to_jd(time):
    """
    datetime类型数据转为儒略日
    """
    tt = time.timetuple()
    return tt.tm_yday


def jd_to_time(time):
    """
    儒略日转换为datetime类型
    """
    time = "2019" + str(time)
    dt = datetime.datetime.strptime(time, '%Y%j').date()
    return dt


def st_loc(num):
    """
    选取气象数据的时候标准化输入为0.5的分辨率
    """
    if num - math.floor(num) <= 0.25 or num - math.floor(num) >= 0.75:
        result = round(num)
    elif 0.25 < num - math.floor(num) < 0.75:
        result = math.floor(num) + 0.5
    else:
        print("经纬度输入错误")
        return 0
    return result


def set_site_data(n, p, k):
    """
    设置站点参数
    NAVAILI::土壤中的有效氮
    PAVAILI::土壤中的有效磷
    KAVAILI::土壤中的有效钾
    """
    site_data = {'SSMAX': 0.,
                 'IFUNRN': 0,
                 'NOTINF': 0,
                 'SSI': 0,
                 'WAV': 30,
                 'SMLIM': 0.3,
                 'RDMSOL': 120,
                 'CO2': 360,
                 'NAVAILI': n,
                 'PAVAILI': p,
                 'KAVAILI': k,
                 'NSOILBASE': 100,
                 'PSOILBASE': 0,
                 'KSOILBASE': 60,
                 'BG_N_SUPPLY': 0.091,
                 'BG_P_SUPPLY': 0,
                 'BG_K_SUPPLY': 0,
                 'NSOILBASE_FR': 0.025,
                 'PSOILBASE_FR': 0.025,
                 'KSOILBASE_FR': 0.025}
    return site_data


def argo_w_modify(agro, row):
    """
    修改播种日期，土壤施肥数据
    argo :: 读取的管理参数字典
    row  :: 列表
    """
    agro[0][datetime.date(2019, 10, 1)]['CropCalendar']['crop_start_date'] = datetime.datetime.strptime(
        row['wintercrop_start_date'], '%Y-%m-%d').date()  # 播期替换
    events_table = [["2019-10-01", 0.6],
                    ["2020-01-15", 0.2],
                    ["2020-04-01", 0.2]]
    fert_table = [["N", row["N_winter_fertilizer"]],
                  ["P", row["P_winter_fertilizer"]],
                  ["K", row["K_winter_fertilizer"]]]
    k = 0
    for i in events_table:
        for j in fert_table:
            agro = w_fertilizer_modify(agro, i[0], k, j[0], i[1] * j[1])
        k += 1
    return agro


def argo_r_modify(agro, row):
    """
    修改播种日期，土壤施肥数据
    argo :: 读取的管理参数字典
    row  :: 列表
    """
    agro[0][datetime.date(2020, 6, 1)]['CropCalendar']['crop_start_date'] = datetime.datetime.strptime(
        row['summercrop_start_date'], '%Y-%m-%d').date()  # 播期替换
    events_table = [["2020-06-01", 0.6],
                    ["2020-08-01", 0.2],
                    ["2020-09-30", 0.2]]
    fert_table = [["N", row["N_summer_fertilizer"]],
                  ["P", row["P_summer_fertilizer"]],
                  ["K", row["K_summer_fertilizer"]]]
    k = 0
    for i in events_table:
        for j in fert_table:
            agro = r_fertilizer_modify(agro, i[0], k, j[0], i[1] * j[1])
        k += 1
    return agro


def w_fertilizer_modify(agro, date, events_no, fert_type, fert_amount):
    """
    修改按时间变化的施肥量
    """
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    agro[0][datetime.date(2019, 10, 1)]['TimedEvents'][1]['events_table'][events_no][date][
        fert_type + '_amount'] = fert_amount
    return agro


def r_fertilizer_modify(agro, date, events_no, fert_type, fert_amount):
    """
    修改按时间变化的施肥量
    """
    date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    agro[0][datetime.date(2020, 6, 1)]['TimedEvents'][1]['events_table'][events_no][date][
        fert_type + '_amount'] = fert_amount
    return agro


def soil_data(s, c, om, b=1.37, rw=0):
    """
    输入参数包括砂粒s、粘粒c、有机质含量om，土壤容重b和碎石子含量Rw(可选)
    输出为永久萎蔫点pwp、田间持水量fc_v、饱和含水量sat_v、饱和最大渗透率Kb(mm/h)单位变为（cm/day）
    """
    # 永久萎蔫点 PWP文中θ1500
    pwp = 1.14*(-0.00024*s+0.00487*c+0.006*om+0.00005*s*om-0.00013*c*om+0.0000068*s*c+0.031)-0.02
    # 田间持水量 FC 文中θ33
    o33 = -0.00251*s+0.00195*c+0.011*om+0.00006*s*om-0.00027*c*om+0.0000452*s*c+0.299
    fc = o33+1.283*o33*o33-0.374*o33-0.015
    # 饱和含水量-FC  θ（S-33）
    s_33 = 1.636*(0.00278*s+0.00034*c+0.022*om-0.00018*s*om-0.00027*c*om-0.0000584*s*c+0.078)-0.107
    # 饱和含水量
    sat = fc+s_33-0.00097*s+0.043
    # 校正后田间持水量与饱和含水量
    pn = 2.65*(1-sat)
    df = b/pn
    if df < 0.9:
        df = 0.9
    elif df > 1.3:
        df = 1.3
    pdf = pn*df
    # 校正过的田间持水量
    fc_v = fc-0.2*(fc+s_33-0.00097*s+0.043-(1-pdf/2.65))
    # 校正后饱和含水量
    sat_v = 1-(pdf/2.65)
    # 饱和导水率mm/h
    y = (np.log(fc_v) - np.log(pwp))/(np.log(1500) - np.log(33))
    ks = 1930 * (np.abs(sat_v - fc_v)) ** (3 - y)
    # gravel校正导水率
    a = b/2.65
    kb_ks = (1 - rw) / (1 - rw * (1 - 3 * a / 2))
    kb = kb_ks * ks
    kb = 2.4 * kb
    return [pwp, fc_v, sat_v, kb]

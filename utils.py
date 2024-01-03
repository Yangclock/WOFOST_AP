import datetime


def time_to_jd(time):
    '''
    datetime类型数据转为儒略日
    '''
    tt = time.timetuple()
    return tt.tm_year * 1000 + tt.tm_yday


def jd_to_time(time):
    '''
    儒略日转换为datetime类型
    '''
    dt = datetime.datetime.strptime(str(time), '%Y%j').date()
    return dt


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
import numpy as np
def soil_data(s, c, om, b=1.37, Rw=0):
    """  
    输入参数包括砂粒s、粘粒c、有机质含量om，土壤容重b和碎石子含量Rw(可选)
    输出为永久萎蔫点pwp、田间持水量fc_v、饱和含水量sat_v、饱和最大渗透率Kb(mm/h)单位变为（cm/day）
    """
    s = s  # sand % (0-100)
    c = c  # clay % (0-100)
    om = om # organic matter % (0-100)
    b = b  # bulk g/cm3 (0-100)
    Rw = Rw  # gravel weight rate (0-1)
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
    if df<0.9:
        df=0.9
    elif df>1.3:
        df=1.3
    pdf = pn*df
    # 校正过的田间持水量
    fc_v = fc-0.2*(fc+s_33-0.00097*s+0.043-(1-pdf/2.65))
    # 校正后饱和含水量
    sat_v = 1-(pdf/2.65)

    # 饱和导水率mm/h
    y = (np.log(fc_v) - np.log(pwp))/(np.log(1500) - np.log(33))
    Ks = 1930*(np.abs(sat_v - fc_v))**(3 - y)
    # gravel校正导水率
    a = b/2.65
    kb_ks = (1-Rw)/(1-Rw*(1-3*a/2))
    Kb = kb_ks*Ks
    Kb = 2.4*Kb
    return [pwp, fc_v, sat_v, Kb]
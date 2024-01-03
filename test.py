import datetime

def time_to_jd(time):
    tt = time.timetuple()
    return tt.tm_year * 1000 + tt.tm_yday

def jd_to_time(time):
    dt = datetime.datetime.strptime(str(time), '%Y%j').date()
    return dt
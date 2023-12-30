import pcse
import pandas as pd
import matplotlib
import yaml
import os
from pcse.fileinput import YAMLCropDataProvider #导入YAML作物模型
from pcse.fileinput import CABOFileReader #导入CABO格式数据

crop_parameter_dir = 'D:\Desktop\WOFOST_AP\crop_parameter'
cropd = YAMLCropDataProvider(crop_parameter_dir)
cropd.set_active_crop('wheat', 'Winter_wheat_103')
print(cropd)
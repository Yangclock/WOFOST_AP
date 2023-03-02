import pcse
import pandas as pd
import matplotlib
import yaml
import os
from pcse.fileinput import YAMLCropDataProvider #导入YAML作物模型
from pcse.fileinput import CABOFileReader #导入CABO格式数据
data_dir = r'E:\2022.11.21毕业论文\3实验过程\WOFOST有效磷\test' #设置工作目录

testcorps = YAMLCropDataProvider(data_dir) #从本地读取Yaml模型库
testcorps.print_crops_varieties()  #输出可选品种
testcorps.set_active_crop('rice','Rice_501') #设定作物类型、品种
print(testcorps) #可输出模型基本参数，也可用于判断模型是否载入正确。

soilfile = os.path.join(data_dir, 'ec3.soil')
soildata = CABOFileReader(soilfile)
print(soildata)

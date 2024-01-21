# coding:utf-8
import arcpy
import os
from arcpy import env
from arcpy.sa import *
"""
Author:地理空间随想录 Date:2024/01/13
获取每一副栅格数据的最大值、最小值等统计信息，然后进行栅格数据的归一化处理！
"""
arcpy.CheckOutExtension("Spatial")
# 文件输入路径及输出路径
env.workspace = r"D:\Biaper\L"
output_path = r"D:\Biaper\L\1"

Rasters = arcpy.ListRasters("*","tif")
for raster in Rasters:
    print raster
    inRaster = raster
    max_Value = arcpy.GetRasterProperties_management(inRaster, "MAXIMUM")
    maxValue = max_Value.getOutput(0)
    print("MAXIMUM:%s" % maxValue)
    min_Value = arcpy.GetRasterProperties_management(inRaster, "MINIMUM")
    minValue = min_Value.getOutput(0)
    print("MINIMUM:%s" % minValue)
    # 计算公式，可以依据需要修改，此处采用(data-min)/(max-min)进行线性缩放到[0,1]之间
    Normalization = (Raster(inRaster) - float(minValue)) / (float(maxValue) - float(minValue))
    filename = os.path.splitext(os.path.basename(inRaster))[0]
    print(filename)
    out = os.path.join(output_path,filename +'.tif')
    Normalization.save(out)
print('处理完成！')
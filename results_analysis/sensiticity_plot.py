import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

file_dir = r"D:\Desktop\WOFOST_AP\simlab_sensitivity_analysis\simlab_results"
simlab_result = pd.read_table(os.path.join(file_dir, "rice_lai_npk.txt"))
print(simlab_result)
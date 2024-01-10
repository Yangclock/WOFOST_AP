import pcse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os, sys
import copy
import datetime as dt
from pcse.fileinput import CABOFileReader, ExcelWeatherDataProvider
from pcse.util import WOFOST71SiteDataProvider
from pcse.base import ParameterProvider
from pcse.fileinput import YAMLAgroManagementReader
from pcse.models import Wofost71_WLP_FD
plt.style.use("ggplot")
print("This notebook was built with:")
print("python version: %s " % sys.version)
print("PCSE version: %s" %  pcse.__version__)
 
data_dir = r'D:\\wofost\\wofost_learn'
 
cropfile = os.path.join(data_dir, 'sug0601.crop')
cropdata = CABOFileReader(cropfile)
 
 
soilfile = os.path.join(data_dir, 'ec3.soil')
soildata = CABOFileReader(soilfile)
sitedata = WOFOST71SiteDataProvider(WAV=100, CO2=360)
 
 
parameters = ParameterProvider(cropdata=cropdata, soildata=soildata,sitedata=sitedata)
 
agromanagement_file = os.path.join(data_dir, 'sugarbeet_calendar.agro')
agromanagement = YAMLAgroManagementReader(agromanagement_file)
 
 
wdp = ExcelWeatherDataProvider(os.path.join(data_dir,'nl1.xlsx'))
 
 
wofost = Wofost71_WLP_FD(parameters, wdp, agromanagement)
wofost1 = Wofost71_WLP_FD(parameters, wdp, agromanagement)
wofost.run_till_terminate()
df = pd.DataFrame(wofost.get_output()).set_index("day")
df.to_excel("wofost_results_enkf.xlsx")
output = wofost.get_output()
 
 
variables_for_DA = ["LAI", "SM"]
dates_of_observation = [dt.date(2006,4,9), dt.date(2006,5,2), dt.date(2006,6,17),
                        dt.date(2006,8,14), dt.date(2006,9,12)]
observed_lai = np.array([0.8, 0.9, 3.2, 4.3, 2.1])
std_lai = observed_lai * 0.05 # Std. devation is estimated as 10% of observed value
observed_sm = np.array([0.285, 0.26, 0.28, 0.18, 0.17])
std_sm = observed_sm * 0.2 # Std. devation is estimated as 5% of observed value
observations_for_DA = []
# Pack them into a convenient format
for d, lai, errlai, sm, errsm in zip(dates_of_observation, observed_lai, std_lai, observed_sm, std_sm):
    observations_for_DA.append((d, {"LAI":(lai, errlai), "SM":(sm, errsm)}))
 
# #画图
# fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16,6))
# df.LAI.plot(ax=axes[0], label="leaf area index")
# axes[0].errorbar(dates_of_observation, observed_lai, yerr=std_lai, fmt="o")
# df.SM.plot(ax=axes[1], label="rootzone soil moisture")
# axes[1].errorbar(dates_of_observation, observed_sm, yerr=std_sm, fmt="o")
# axes[0].set_title("Leaf area index")
# axes[1].set_title("Volumetric soil moisture")
# fig.autofmt_xdate()
# plt.show()
 
 
ensemble_size = 50
np.random.seed(10000)
# A container for the parameters that we will override
override_parameters = {}
#Initial conditions
override_parameters["TDWI"] = np.random.normal(0.51, 0.05, (ensemble_size))
override_parameters["WAV"] = np.random.normal(4.5, 1.5, (ensemble_size))
# parameters
override_parameters["SPAN"] = np.random.normal(35, 3 ,(ensemble_size))
override_parameters["SMFCF"] = np.random.normal(0.30, 0.03 ,(ensemble_size))
fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(12,10))
# Show the sample that was drawn
for ax, (par, distr) in zip(axes.flatten(), override_parameters.items()):
    ax.hist(distr)
    ax.set_title(par)
 
ensemble = []
for i in range(ensemble_size):
    p = copy.deepcopy(parameters)
    for par, distr in override_parameters.items():
        p.set_override(par, distr[i])
    member = Wofost71_WLP_FD(p, wdp, agromanagement)
    ensemble.append(member)
show_output = False
count = 0
 
while count<5:
    count+=1
    day, obs = observations_for_DA.pop(0)
    for member in ensemble:
        member.run_till(day)
    wofost1.run_till(day)
    print("Ensemble now at day %s" % member.day)
    print("%s observations left!" % len(observations_for_DA))
 
    collected_states = []
    for member in ensemble:
        t = {}
        for state in variables_for_DA:
            t[state] = member.get_variable(state)
        collected_states.append(t)
    df_A = pd.DataFrame(collected_states)
    A = np.matrix(df_A).T
    df_A if show_output else None
    P_e = np.matrix(df_A.cov())
    df_A.cov() if show_output else None
 
 
    perturbed_obs = []
    for state in variables_for_DA:
        (value, std) = obs[state]
        d = np.random.normal(value, std, (ensemble_size))
        perturbed_obs.append(d)
    df_perturbed_obs = pd.DataFrame(perturbed_obs).T
    df_perturbed_obs.columns = variables_for_DA
    D = np.matrix(df_perturbed_obs).T
    R_e = np.matrix(df_perturbed_obs.cov())
    df_perturbed_obs if show_output else None
    # Here we compute the Kalman gain
    H = np.identity(len(obs))
    K1 = P_e * (H.T)
    K2 = (H * P_e) * H.T
    K = K1 * ((K2 + R_e).I)
    K if show_output else None
 
    # Here we compute the analysed states
 
    Aa = A + K * (D - (H * A))
 
    df_Aa = pd.DataFrame(Aa.T, columns=variables_for_DA)
    update = df_Aa.mean(axis=0)
    print(update)
    df_Aa if show_output else None
 
for member, new_states in zip(ensemble, df_Aa.itertuples()):
    r1 = member.set_variable("LAI", new_states.LAI)
    r2 = member.set_variable("SM", new_states.SM)
for member in ensemble:
    member.run_till_terminate()
    results = []
for member in ensemble:
    member_df = pd.DataFrame(member.get_output()).set_index("day")
    results.append(member_df)
fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(16,16))
for member_df in results:
    member_df["LAI"].plot(style="k:", ax=axes[0])
    member_df["SM"].plot(style="k:", ax=axes[1])
axes[0].errorbar(dates_of_observation, observed_lai, yerr=std_lai, fmt="o")
axes[1].errorbar(dates_of_observation, observed_sm, yerr=std_sm, fmt="o")
axes[0].set_title("Leaf area index")
axes[1].set_title("Volumetric soil moisture")
fig.autofmt_xdate()
plt.show()

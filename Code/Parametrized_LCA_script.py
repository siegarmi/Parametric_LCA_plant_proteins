import bw2data as bd
import bw2io as bi
from bw2data.parameters import *
import datetime as dt
import numpy as np
import pandas as pd
from tqdm import tqdm

import lca_algebraic as agb

from sympy import init_printing
import bw2io as bi
from ecoinvent_interface import Settings

from bw_base_set_up import bw_set_up, regionalize_db

from import_agrifootprint_db_functions import import_agrifootprint

from Parametrized_LCA_functions import *

np.random.seed(42)

# Pretty print for Sympy
init_printing()

csv_path = ".../Parametric_LCA_plant_proteins/" #set path to main project folder --> has to be changed manually if file path is different

now = dt.datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M")

class ProductionLocationError(Exception):
    pass

bd.projects.dir

#Setting project name
project = "Parametrized LCA"
bd.projects.set_current(project)

#Load ecoinvent database
ei_reg_name = "ecoinvent-3.10-cutoff"
bio_name = "ecoinvent-3.10-biosphere"

#enter username and password for ecoinvent database below
my_settings = Settings(username="...", password="...")
if ei_reg_name in bd.databases and bio_name in bd.databases:
    print(ei_reg_name + " and " + bio_name + " have already been imported.")
elif ei_reg_name in bd.databases and not bio_name in bd.databases:
    print(ei_reg_name + " has already been imported." + bio_name + " is missing. Please, delete " + ei_reg_name + " and run the command again.")
else:
    bi.import_ecoinvent_release("3.10","cutoff",my_settings.username,my_settings.password)

eidb = bd.Database(ei_reg_name)
bio3 = bd.Database(bio_name)

#Import agrifootprint database
import_agrifootprint(ei_reg_name,bio_name)

af_reg_name = "agrifootprint 6.3 all allocations"
afdb = bd.Database(af_reg_name)

#Setting up regionalized databases and impact assessment methods --> this can last up to one day depending on the power of your computer! Has to be done only once.
bw_set_up()
regionalize_db(ei_reg_name)
regionalize_db(af_reg_name)

af_reg_name = "agrifootprint 6.3 all allocations_regionalized"
ei_reg_name = "ecoinvent-3.10-cutoff_regionalized"

eidb_reg = bd.Database(ei_reg_name)
afdb_reg = bd.Database(af_reg_name)

bio_water_name = "biosphere water regionalized"
bio_luluc_name = "biosphere luluc regionalized"
bio_pm_name = "biosphere pm regionalized"

bio_water = bd.Database(bio_water_name)
bio_luluc = bd.Database(bio_luluc_name)
bio_pm = bd.Database(bio_pm_name)

#Load input data files for transport, cultivation, and electricity mixes
european_countries = pd.read_csv(f"{csv_path}Data input/Input_files_csv/transport/European_countries.csv", sep = ";", dtype= {"Country": str, "Code": str})
production_countries_soy_Europe = pd.read_csv(f"{csv_path}Data input/Input_files_csv/production_countries/production_countries_soy_Europe.csv", sep = ";",header=None)[0].to_list()
production_countries_pea_Europe = pd.read_csv(f"{csv_path}Data input/Input_files_csv/production_countries/production_countries_pea_Europe.csv", sep = ";",header=None)[0].to_list()
production_countries_wheat_Europe = pd.read_csv(f"{csv_path}Data input/Input_files_csv/production_countries/production_countries_wheat_Europe.csv", sep = ";",header=None)[0].to_list()
distances_european_countries = pd.read_csv(f"{csv_path}Data input/Input_files_csv/transport/Distances_european_countries_final.csv", sep = ";", decimal = ".", dtype= {"filename": np.int32, "country1": str, "country2": str, "mean": np.float64, "std": np.float64, "min": np.float64, "0.25": np.float64, "0.5": np.float64, "0.75": np.float64, "max": np.float64,  "scipy_mean": np.float64, "scipy_variance": np.float64, "scipy_skewness": np.float64, "scipy_kurtosis": np.float64, "scipy_min": np.float64, "scipy_max": np.float64})
production_to_port_distance = pd.read_csv(f"{csv_path}Data input/Input_files_csv/transport/Production_to_port_distance.csv", sep = ";", decimal = ".", dtype= {"Country ID": str, "Crop": str, "mean": np.float64, "sd": np.float64})
transport_between_ports = pd.read_csv(f"{csv_path}Data input/Input_files_csv/transport/Transport_between_ports.csv", sep = ";", decimal = ".", dtype= {"shipping": str, "shipping ID": str, "Destination": str, "Destination ID": str, "Crop": str, "Mean distance": np.float64, "Sd distance": np.float64})
europe_distance_from_port = pd.read_csv(f"{csv_path}Data input/Input_files_csv/transport/Europe_distance_from_port.csv", sep = ";", decimal = ".", dtype= {"Country": str, "ID": str, "Mean dist": np.float64, "Sd dist": np.float64})

electricity_share_CN_pea = pd.read_csv(f"{csv_path}Data input/Input_files_csv/grid_shares/Electricity_grid_shares_CN_pea.csv", sep = ";", decimal = ".", dtype= {"Region": str, "Grid": str, "Area": np.float64, "Share": np.float64})
electricity_share_CN_soy = pd.read_csv(f"{csv_path}Data input/Input_files_csv/grid_shares/Electricity_grid_shares_CN_soy.csv", sep = ";", decimal = ".", dtype= {"Region": str, "Grid": str, "Area": np.float64, "Share": np.float64})
electricity_share_CN_wheat = pd.read_csv(f"{csv_path}Data input/Input_files_csv/grid_shares/Electricity_grid_shares_CN_wheat.csv", sep = ";", decimal = ".", dtype= {"Region": str, "Grid": str, "Area": np.float64, "Share": np.float64})
electricity_share_US_soy = pd.read_csv(f"{csv_path}Data input/Input_files_csv/grid_shares/Electricity_grid_shares_US_soy.csv", sep = ";", decimal = ".", dtype= {"Region": str, "Grid": str, "Area": np.float64, "Share": np.float64})
electricity_share_US_wheat = pd.read_csv(f"{csv_path}Data input/Input_files_csv/grid_shares/Electricity_grid_shares_US_wheat.csv", sep = ";", decimal = ".", dtype= {"Region": str, "Grid": str, "Area": np.float64, "Share": np.float64})

#Load specifications for value chains
value_chains = pd.read_csv(f"{csv_path}Data input/Input_files_csv/Parameterized_model/Value_chains.csv", sep = ";")

print("Starting analysis.")

#Iterate through all value chains to calculate environmental impacts
for index in range(len(value_chains)):

    track_change = []

    product = value_chains.iloc[index]["Product"]

    #Identifying where transport takes place and preparing name strings to identify results of each value chain
    row = value_chains.loc[index, [col for col in value_chains.columns if "transport" not in col.lower() and "product" not in col.lower()]]
    row = row.dropna()
    processing_locations = [(col, str(val)[-2:]) for col, val in row.items()]
    locations_dictionary = dict(processing_locations)
    transport = [
    col.split()[-1] for col in value_chains.columns
    if value_chains.iloc[index][col] == "Yes"
    ]

    if not processing_locations:
        location_string = ""
    else:
        cultivation_loc = processing_locations[0][1]
        point_of_use_loc = processing_locations[-1][1]
        processing_loc = [val for _, val in processing_locations[1:-1]]

        seen = set()
        unique_processing_loc = []
        for val in processing_loc:
            if val not in seen:
                unique_processing_loc.append(val)
                seen.add(val)

        # Build the final location string
        all_locations = [cultivation_loc] + unique_processing_loc + [point_of_use_loc]
        location_string = "-".join(all_locations)

    print(f"Analysis for {product} in locations {location_string}.")
    #country_name = f"_{location}"

    #Create missing agricultural production processes, if any
    crop_name, crop_name_short = get_crop_name(product)
    check_if_agricultural_activities_exist_and_create_them_if_not(locations_dictionary["Cultivation"],crop_name,production_countries_pea_Europe,production_countries_soy_Europe,production_countries_wheat_Europe,distances_european_countries,eidb_reg,afdb_reg)
    
    #Load input data for process parameters and parametrized formulas
    name_process = f"Formulas_{product}"
    input_parameters = pd.read_csv(f"{csv_path}Data input/Input_files_csv/Parameterized_model/General_parameters.csv", sep = ";", decimal = ".")
    formulas = pd.read_csv(f"{csv_path}Data input/Input_files_csv/Parameterized_model/{name_process}.csv", sep = ";", decimal = ".")
    if product == "SPI" or product == "PPI":
        string = f"{formulas.iloc[0,0]}_protein_isolation"
    elif product == "SPC" or product == "PPC":
        string = f"{formulas.iloc[0,0]}_protein_concentration"
    else:
        string = f"{formulas.iloc[0,0]}_{formulas.iloc[-1]["Process"]}"
    input_data = input_parameters[input_parameters.iloc[:, 0].str.contains(string, na=False)]
    input_data = input_data.reset_index(drop=True)

    #Reset foregroud database before creating new processes
    user_db = "ForegroundDB"
    agb.resetDb(user_db)
    agb.resetParams()
    agb.list_databases()

    #Create parameters based on specifications in input data
    for i in range(0,len(input_data)):
        create_params(name=input_data.iloc[i]["Name"],distribution=input_data.iloc[i]["Distribution"],minimum=input_data.iloc[i]["min"],maximum=input_data.iloc[i]["max"],mean=input_data.iloc[i]["mean/mode"],sd=input_data.iloc[i]["sd"])
    
    #Create transport parameters
    for key, location in locations_dictionary.items():
        if key.lower() in transport:
            process_location = location
            location_last_process = locations_dictionary[last_key]
            transport_parameters = calculate_transport_parameters(process_location, location_last_process, crop_name, european_countries, distances_european_countries, production_to_port_distance, transport_between_ports, europe_distance_from_port)
            for parameters in transport_parameters:
                create_params(name=f'{key}_{parameters[0]}',distribution="NORMAL",minimum=parameters[-1].loc["minimum"].iloc[0],maximum=parameters[-1].loc["maximum"].iloc[0],mean=parameters[-1].loc["loc"].iloc[0],sd=parameters[-1].loc["scale"].iloc[0])
        last_key = key

    params = agb.all_params()

    #Select background activities that are required, if necessary create new electricity and heat production processes for specific location
    activities = {}
    locations = []
    activities["cultivation"] = {}
    activities["transport"] = {}

    activities["transport"]["transport_lorry_europe"] = agb.findActivity('transport, freight, lorry, all sizes, EURO6 to generic market for transport, freight, lorry, unspecified',loc="RER",db_name=ei_reg_name,case_sensitive = True)
    activities["transport"]["transport_lorry_global"] = agb.findActivity('transport, freight, lorry, all sizes, EURO6 to generic market for transport, freight, lorry, unspecified',loc="RoW",db_name=ei_reg_name,case_sensitive = True)
    activities["transport"]["transport_ship"] = agb.findActivity('market for transport, freight, sea, container ship',loc="GLO",db_name=ei_reg_name,case_sensitive = True)

    for key, location in locations_dictionary.items():
        if key == "Cultivation":
            if crop_name == "Peas":
                activities["cultivation"]["input_crop"] = agb.findActivity(name=f'Peas, dry, dried, at storage {{{location}}} Economic, U',loc=location,db_name=af_reg_name)
            elif crop_name == "Soybeans":
                activities["cultivation"]["input_crop"] = agb.findActivity(name=f'Soybeans, dried, at storage {{{location}}} Economic, U',loc=location,db_name=af_reg_name)
            else:
                activities["cultivation"]["input_crop"] = agb.findActivity(name=f'Wheat grain, dried, at storage {{{location}}} Economic, U',loc=location,db_name=af_reg_name)
                
        elif key == "Point_of_use":
            continue
        elif location in locations:
            continue
        else:
            activities[location] = {}
            if location == "CN" and crop_name == "Peas":
                create_electricity_market_group_processes("CN-SGCC",electricity_share_CN_pea,"Pea",eidb_reg)
                activities[location]["electricity_mix"] = agb.findActivity(name="market group for electricity used in Pea processing, low voltage",loc=location,db_name=ei_reg_name)
            elif location == "CN" and crop_name == "Soybeans":
                create_electricity_market_group_processes("CN-SGCC",electricity_share_CN_soy,"Soy",eidb_reg)
                activities[location]["electricity_mix"] = agb.findActivity(name="market group for electricity used in Soy processing, low voltage",loc=location,db_name=ei_reg_name)
            elif location == "CN" and crop_name == "Wheat":
                create_electricity_market_group_processes("CN-SGCC",electricity_share_CN_wheat,"Wheat",eidb_reg)
                activities[location]["electricity_mix"] = agb.findActivity(name="market group for electricity used in Wheat processing, low voltage",loc=location,db_name=ei_reg_name)
            elif location == "US" and crop_name == "Soybeans":
                create_electricity_market_group_processes("US",electricity_share_US_soy,"Soy",eidb_reg)
                activities[location]["electricity_mix"] = agb.findActivity(name="market group for electricity used in Soy processing, low voltage",loc=location,db_name=ei_reg_name)
            elif location == "US" and crop_name == "Wheat":
                create_electricity_market_group_processes("US",electricity_share_US_wheat,"Wheat",eidb_reg)
                activities[location]["electricity_mix"] = agb.findActivity(name="market group for electricity used in Wheat processing, low voltage",loc=location,db_name=ei_reg_name)
            else:
                activities[location]["electricity_mix"] = agb.findActivity(name="market for electricity, low voltage",loc=location,db_name=ei_reg_name)

            create_heat_production_process(location,eidb_reg,crop_name,track_change,european_countries)
            activities[location]["heat_mix"] = agb.findActivity(name="heat production, natural gas, at boiler modulating >100kW",loc=location,db_name=ei_reg_name)

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for tap water' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for tap water',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["tap_water"] = activity

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for wastewater, average' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for wastewater, average',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["wastewater"] = activity

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for biowaste' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for biowaste',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["biowaste"] = activity

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for ethanol, without water, in 99.7% solution state, from ethylene' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for ethanol, without water, in 99.7% solution state, from ethylene',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["ethanol"] = activity

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for sodium hydroxide, without water, in 50% solution state' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for sodium hydroxide, without water, in 50% solution state',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["sodium_hydroxide"] = activity

            activity_temp = [act for act in eidb_reg if act["name"] == 'market for hydrochloric acid, without water, in 30% solution state' and act["location"] == location]
            activity_temp = findlocation(activity_temp,'market for hydrochloric acid, without water, in 30% solution state',location,crop_name,track_change,eidb_reg,european_countries)
            activity = activity_temp[0]
            activities[location]["hydrochloric_acid"] = activity

            activities[location]["hexane"] = agb.findActivity('market for hexane',loc="GLO",db_name=ei_reg_name)
            activities[location]["hexane_emissions"] = agb.findActivity('Hexane',categories=["air",],db_name=bio_name,case_sensitive = True)

            locations.append(location)

    
    for activity_group in activities.values():
        for activity in activity_group.values():
            activity.updateMeta(phase=activity)

    #Create transport activities
    activities["foreground"] = {}

    for key, location in locations_dictionary.items():
        exchanges_input = {}
        if key.lower() in transport:
            if key != "Point_of_use":
                formula = formulas[formulas["Process"] == key.lower()].iloc[0]["Formula"]
            else:
                formula = formulas.iloc[-2]["Formula"]

            for key_transport_param, value_transport_param in params.items():
                if f"{key}_transport" in key_transport_param:
                    transport_formula = f'({formula}) * params["{value_transport_param}"] / 1000' #divided by 1000 to convert kg of transported good into tons because unit is tkm
                    if "origin" in key_transport_param:
                        exchanges_input[activities["transport"]["transport_lorry_global"]] = eval(transport_formula)
                    elif "shipping" in key_transport_param:
                        exchanges_input[activities["transport"]["transport_ship"]] = eval(transport_formula)
                    else:
                        exchanges_input[activities["transport"]["transport_lorry_europe"]] = eval(transport_formula)
            print(exchanges_input)
            activities["foreground"][f"Transport_to_{key.lower()}"] = agb.newActivity(user_db,
                f"Transport_to_{key.lower()}",
                "ton kilometer",
                exchanges= exchanges_input)
     
    #Create foreground activities based on input data and link to background activities
    for key, location in locations_dictionary.items():
        if key == "Cultivation":
            continue     
        elif key == "Point_of_use":
            continue
        else:
            print(key)
            exchanges_input = {}
            activity = formulas[formulas["Process"] == key.lower()]
            counter = 0
            for exchange in activity["Flow"]:
                if "allocation" in exchange or "protein" in exchange:
                    counter += 1
                elif "input_crop" in exchange:
                    exchanges_input[activities["cultivation"][exchange]] = eval(activity["Formula"].iloc[counter])
                    counter += 1
                elif crop_name_short in exchange:
                    exchanges_input[activities["foreground"][exchange]] = eval(activity["Formula"].iloc[counter])
                    counter += 1
                else:
                    exchanges_input[activities[location][exchange]] = eval(activity["Formula"].iloc[counter])
                    counter += 1
            for key_transport in activities["foreground"]:
                if f"Transport_to_{key.lower()}" in key_transport:
                    exchanges_input[activities["foreground"][key_transport]] = 1
            print(exchanges_input)
            activities["foreground"][f"{crop_name_short}_{key.lower()}"] = agb.newActivity(user_db,
                f"{crop_name_short}_{key.lower()}",
                "kg",
                exchanges= exchanges_input)

    #Create total inventory (final activity) to consider uncertainty in allocation factor of final activity and protein content
    exchanges_input = {}
    exchanges_input[activities["foreground"][f"{formulas.iloc[-1]["Crop"]}_{formulas.iloc[-1]["Process"]}"]] = eval(formulas.iloc[-2]["Formula"])
    for key_transport in activities["foreground"]:
        if f"Transport_to_point_of_use" in key_transport:
            exchanges_input[activities["foreground"][key_transport]] = 1
    print(exchanges_input)
    total_inventory = agb.newActivity(user_db,
        "total_inventory",
        "kg",
        exchanges= exchanges_input)

    #Define impact categories
    impacts = [agb.findMethods('GWP_100a', mainCat='IPCC_AR6')[0],agb.findMethods('GWP_100a', mainCat='IPCC_AR6')[1],agb.findMethods('GWP_100a', mainCat='IPCC_AR6')[2],agb.findMethods('GWP_100a', mainCat='IPCC_AR6')[3],agb.findMethods('Particulate matter', mainCat='PM regionalized')[0],agb.findMethods('Water stress', mainCat='AWARE regionalized')[0],agb.findMethods('Occupation', mainCat='Biodiversity regionalized')[0],agb.findMethods('Transformation', mainCat='Biodiversity regionalized')[0]]    
    
    #Calculate 100000 values for each parameter based on their respective distribution
    n_iter = 100000
    param_values = params.copy()
    for param in params:
        if params[param].distrib == "fixed":
            param_values[param] = np.array([params[param].default] * n_iter)
        else:
            random_array = np.random.rand(1,n_iter)[0]
            param_values[param] = np.array(params[param].rand(random_array))

    #Contribution analysis: Run the model for each process in the foreground inventory + the electricity and heat demand in the protein extraction step to get the contributions of each subprocess. The functional unit is individually adapted based on the allocation parameters.
    LCIA_results_contribution_temp = {}
    functional_values = []
    count = 0
    for process in formulas["Process"].unique()[::-1]:
        print(process)
        if process == "crop":
            upstream_activity = [value for key, value in activities["cultivation"].items() if process in key and "Transport" not in key][0]
        else:
            upstream_activity = [value for key, value in activities["foreground"].items() if process in key and "Transport" not in key][0]
        if count == 0:
            index_functional_value = -2
        else:
            index_functional_value = formulas.index[formulas["Flow"].str.contains(f"{process}_allocation", na=False)].to_list()[0]+1
        functional_values.append(formulas.iloc[index_functional_value]["Formula"])
        functional_value_formula = "*".join(functional_values)
        functional_value = 1/eval(functional_value_formula)
        LCIA_results_contribution_temp[process] = agb.compute_impacts(
            upstream_activity,
            impacts,
            functional_unit=functional_value,
            **param_values)
        LCIA_results_contribution_temp[process] = LCIA_results_contribution_temp[process].reset_index(drop=True)
        if [value for key, value in activities["foreground"].items() if process in key and "Transport" in key]:
            transport_activity = [value for key, value in activities["foreground"].items() if process in key and "Transport" in key][0]
            LCIA_results_contribution_temp[f"Transport_to_{process}"] = agb.compute_impacts(
                transport_activity,
                impacts,
                functional_unit=functional_value,
                **param_values)
            LCIA_results_contribution_temp[f"Transport_to_{process}"] = LCIA_results_contribution_temp[f"Transport_to_{process}"].reset_index(drop=True)
        count += 1

    try:
        transport_activity = [value for key, value in activities["foreground"].items() if "point_of_use" in key and "Transport" in key][0]
        LCIA_results_contribution_temp[f"Transport_to_point_of_use"] = agb.compute_impacts(
            transport_activity,
            impacts,
            functional_unit=1,
            **param_values)
        LCIA_results_contribution_temp[f"Transport_to_point_of_use"] = LCIA_results_contribution_temp[f"Transport_to_point_of_use"].reset_index(drop=True)
    except IndexError:
        print("No transport to point-of-use was modelled.")

    electricity_source = activities[locations_dictionary["Protein_separation"]]["electricity_mix"]
    electricity_input = formulas.loc[(formulas["Flow"] == "electricity_mix") & (formulas["Process"] == formulas["Process"].unique()[-1]), "Formula"].iloc[0]
    allocation_value = formulas.iloc[-2]["Formula"]
    functional_value = 1/eval(electricity_input + "*" + allocation_value)

    LCIA_results_electricity_protein_separation = agb.compute_impacts(
        electricity_source,
        impacts,
        functional_unit=functional_value,
        **param_values)

    LCIA_results_electricity_protein_separation = LCIA_results_electricity_protein_separation.reset_index(drop=True)

    try:
        heat_source = activities[locations_dictionary["Protein_separation"]]["heat_mix"]
        heat_input = formulas.loc[(formulas["Flow"] == "heat_mix") & (formulas["Process"] == formulas["Process"].unique()[-1]), "Formula"].iloc[0]
        functional_value = 1/eval(heat_input + "*" + allocation_value)

        LCIA_results_heat_protein_separation = agb.compute_impacts(
                heat_source,
                impacts,
                functional_unit=functional_value,
                **param_values)

        LCIA_results_heat_protein_separation = LCIA_results_heat_protein_separation.reset_index(drop=True)
    except IndexError:
        print("No heat used in this process.")
        LCIA_results_heat_protein_separation = pd.DataFrame({"GWP_100a - all[CO2-eq]": np.zeros(100000), "GWP_100a - Biogenic[CO2-eq]": np.zeros(100000), "GWP_100a - Fossil[CO2-eq]": np.zeros(100000), "GWP_100a - LUC[CO2-eq]": np.zeros(100000), "Particulate matter - health impacts (PMHI)[DALY]":np.zeros(100000), "Water stress - Annual[m3 world]":np.zeros(100000), "Occupation - Biodiversity loss (LUBL)[PDF*year/m2a]":np.zeros(100000) , "Transformation - Biodiversity loss (LUBL)[PDF*year/m2]":np.zeros(100000)})
    
    #Set funtional value to 1 to run the model for the final inventory based on 1kg of product or protein as defined above
    functional_value = 1

    #Run model for total inventory and store results and parameter values
    LCIA = agb.compute_impacts(
        total_inventory,
        impacts,
        functional_unit=functional_value,
        return_params = True,
        **param_values)
    LCIA_results = LCIA.dataframes["Results"]
    LCIA_results = LCIA_results.reset_index(drop=True)
    LCIA_parameters = LCIA.dataframes["Parameters"]
    LCIA_parameters.index = LCIA_parameters.index.get_level_values("name")
    LCIA_results_protein = LCIA_results.copy()
    for i in range(n_iter):
        protein_content = LCIA_parameters.loc[LCIA_parameters.index.str.contains("protein_out"),f"value_{i+1}"].iloc[0]
        LCIA_results_protein.iloc[i] = LCIA_results_protein.iloc[i] / protein_content
    filename_results = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_overall.csv"
    filename_results_protein = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_overall_protein.csv"
    filename_parameters = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_parameters_contribution_analysis.csv"
    LCIA_results.to_csv(filename_results,index=True)
    LCIA_results_protein.to_csv(filename_results_protein,index=True)
    #LCIA_parameters.to_csv(filename_parameters,index=True)

    #Calculate effective results of the contribution analysis by subtracting the impacts of the upstream processes from each process in the foreground inventory to isolate its impact. This is done for each of the 100000 model runs. Results are saved to csv files.
    LCIA_results_contribution, LCIA_results_contribution_protein = calculate_results_process_contribution(LCIA_results_contribution_temp,LCIA_results_electricity_protein_separation,LCIA_results_heat_protein_separation,formulas,transport,LCIA_parameters,n_iter)

    filename = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_contribution_analysis.csv"
    filename_protein = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_contribution_analysis_protein.csv"
    LCIA_results_contribution.to_csv(filename,index=True)
    #LCIA_results_contribution_protein.to_csv(filename_protein,index=True)

    #Calculate one-at-a-time sensitivity analysis for the final inventory
    oat_matrix = agb.oat_matrix(
        total_inventory,
        impacts,
        functional_unit=functional_value)
    filename = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_oat_matrix.csv"

    #Calculate 1st-order Sobol-indices for the total inventory. Can be changed to total sobol indices by changing s1 to st.
    sobol_indices = agb.incer_stochastic_matrix(
        total_inventory,
        impacts,
        functional_unit=functional_value)
    oat_matrix.index.tolist()
    sobol_df = pd.DataFrame(sobol_indices.s1,columns = impacts, index = oat_matrix.index.tolist())
    filename = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_sobol_indices.csv"
    sobol_df.to_csv(filename,index=True)

    sobol_df_total = pd.DataFrame(sobol_indices.st,columns = impacts, index = oat_matrix.index.tolist())
    filename = f"{csv_path}Parametrized_LCA_results/{product}_{location_string}_results_sobol_indices_total.csv"
    sobol_df_total.to_csv(filename,index=True)

    df_track_change = pd.DataFrame(track_change,columns = ["Location of change","Change made"])
    filename = f"{csv_path}Track_change/track_change_{product}_{location_string}.csv"
    df_track_change.to_csv(filename,index=False)
    print(f"Changes made during modelling are saved as: {filename}")
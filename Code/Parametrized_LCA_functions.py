import lca_algebraic as agb
import bw2data as bd
import numpy as np
import pandas as pd

def isNaN(num):
    return num != num
def isinEurope(country, reference):
    test = country in list(reference["Code"])
    return test

#function that tests if process was found in ecoinvent background database for selected region. If not, it chooses a coarser region until the process is found in ecoinvent. Saves all changes in track change file.
def findlocation(created_exchange,activity_name,country,crop,track_change,db,european_countries):
    country_ini = country
    if created_exchange == [] and "market for electricity, low voltage" == activity_name:
        if country == "CN" and crop == "Peas":
            activity_name = "market group for electricity used in Pea processing, low voltage"
        elif country == "CN" and crop == "Soybeans":
            activity_name = "market group for electricity used in Soy processing, low voltage"
        elif country == "CN" and crop == "Wheat":
            activity_name = "market group for electricity used in Wheat processing, low voltage"
        elif country == "US" and crop == "Soybeans":
            activity_name = "market group for electricity used in Soy processing, low voltage"
        elif country == "US" and crop == "Wheat":
            activity_name = "market group for electricity used in Wheat processing, low voltage"
        else:
            activity_name = "market group for electricity, low voltage"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        if created_exchange != []:
            track_change.append((str(created_exchange[0]),f"Name has been changed from market for electricity, low voltage to {activity_name}"))
    if created_exchange == [] and isinEurope(country,european_countries) and activity_name == "market for natural gas, high pressure":
        country = "RoE"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        if created_exchange != []:
            track_change.append((str(created_exchange[0]),"Location has been changed from " + country_ini + " to " + country + " because no " + str(created_exchange[0]) + " with the location " + country_ini + " exists in background databases."))
    elif created_exchange == [] and isinEurope(country,european_countries) and (activity_name == "market for tap water" or activity_name == "market for wastewater, average"):
        country = "Europe without Switzerland"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        if created_exchange != []:
            track_change.append((str(created_exchange[0]),"Location has been changed from " + country_ini + " to " + country + " because no " + str(created_exchange[0]) + " with the location " + country_ini + " exists in background databases."))
    elif created_exchange == [] and isinEurope(country,european_countries):
        country = "RER"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        if created_exchange != []:
            track_change.append((str(created_exchange[0]),"Location has been changed from " + country_ini + " to " + country + " because no " + str(created_exchange[0]) + " with the location " + country_ini + " exists in background databases."))
    if created_exchange == []:
        country = "RoW"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        if created_exchange != []:
            track_change.append((str(created_exchange[0]),"Location has been changed from " + country_ini + " to " + country + " because no " + str(created_exchange[0]) + " with the location " + country_ini + " exists in background databases."))
    if created_exchange == []:
        country = "GLO"
        created_exchange = [act for act in db if activity_name == act['name'] and country == act['location']]
        track_change.append((str(created_exchange[0]),"Location has been changed from " + country_ini + " to " + country + " because no " + str(created_exchange[0]) + " with the location " + country_ini + " exists in background databases."))

    return created_exchange

#Function to create country specific heat production processes based on "heat production, natural gas, at boiler modulating >100kW" in "CA-QC"
def create_heat_production_process(country,eidb_reg,crop,track_change,european_countries):
    for activity in [act for act in eidb_reg if "custom_heat_process_" + str(country) in act['code'] and country in act['location']]:
        activity.delete()

    original_process = [act for act in eidb_reg if act['name'] == "heat production, natural gas, at boiler modulating >100kW" and "CA-QC" in act['location']][0]
    new_activity = original_process.copy(code="custom_heat_process_"+country,name=original_process["name"],location=country)
    new_activity.save()

    track_change.append(("Heat production activity","Heat production process has been created for " + country + " based on heat production, natural gas, at boiler modulating >100kW (CA-QC)."))

    for exchange in new_activity.exchanges():
        code = exchange["input"][1]
        db = exchange["input"][0]
        input_act = [act for act in bd.Database(db) if act["code"] == code][0]
        if input_act.get("location"):
            if exchange["type"] != "production" and (input_act["location"] == "CA-QC" or input_act["location"] == "CA"):
                amount = exchange["amount"]
                unit = exchange["unit"]
                type = exchange["type"]
                exchange.delete()
                exchange_substitution_temp = [act for act in bd.Database(db) if act['name'] == input_act["name"] and act['location'] == country]
                exchange_substitution_temp = findlocation(exchange_substitution_temp,input_act["name"],country,crop,track_change,bd.Database(db),european_countries)
                exchange_substitution = exchange_substitution_temp[0]
                new_activity.new_exchange(input=exchange_substitution.key, amount = amount, unit = unit, type = type).save()
        
    new_activity.save()

#Function to create electricity market groups based on production volumes of cultivation areas
def create_electricity_market_group_processes(country,grid_shares,product,db):
    for activity in [act for act in db if "market group for electricity used in " + product + " processing, low voltage" == act["name"] and country[:2] in act["location"]]:
        activity.delete()
    existing_electricity_market_group = [act for act in db if "market group for electricity, low voltage" == act['name'] and country == act['location']][0]

    new_electricity_market_group = existing_electricity_market_group.copy()
    new_electricity_market_group["name"] = "market group for electricity used in " + product + " processing, low voltage"
    if country == "CN-SGCC":
        new_electricity_market_group["location"] = "CN"
        new_electricity_market_group.save()
    for exchange in [exc for exc in new_electricity_market_group.exchanges() if exc["type"] == "technosphere"]:
        exchange_input = [act for act in db if exchange["input"][1] == act['code']][0]
        if exchange_input["location"] in grid_shares["Grid"].to_list():
            exchange["amount"] = grid_shares.loc[grid_shares["Grid"]==exchange_input["location"]]["Share"].to_list()[0]
            exchange.save()
        else:
            exchange.delete()
    if country == "CN-SGCC":
        central_grid = [act for act in db if "market for electricity, low voltage" == act['name'] and "CN-CSG" == act['location']][0]
        new_electricity_market_group.new_exchange(input=central_grid.key,amount=grid_shares.loc[grid_shares["Grid"]=="CN-CSG"]["Share"].to_list()[0],unit="kilowatt hour",type="technosphere").save()
        new_electricity_market_group.new_exchange(input=new_electricity_market_group.key,amount=1,unit="kilowatt hour",type="production").save()
    new_electricity_market_group.save()
    print(new_electricity_market_group)

def get_crop_name(product):
    if product == "SPI" or product == "SPC":
        crop_name = "Soybeans"
        crop_name_short = "Soy"
    elif product == "PPI" or product == "PPC":
        crop_name = "Peas"
        crop_name_short = "Pea"
    elif product == "gluten":
        crop_name = "Wheat"
        crop_name_short = "Wheat"
    else:
        raise SystemExit("Code currently not set up for provided product. Please update function get_crop_name to include the product. Stopping execution.")
    return crop_name, crop_name_short

def find_closest_production_country_to_create_new_production_processes(production_location,production_countries_Europe,distances_european_countries):
    mean_distances = []
    for country in production_countries_Europe:
        mean_distances.append(distances_european_countries.loc[(country[-2:] == distances_european_countries["country1 ID"]) & (production_location[-2:] == distances_european_countries["country2 ID"]) | (country[-2:] == distances_european_countries["country2 ID"]) & (production_location[-2:] == distances_european_countries["country1 ID"])]["mean"].iloc[0])
    closest_country = production_countries_Europe[mean_distances.index(min(mean_distances))]
    return closest_country

#Function to create new agricultural production processes, if any, by e.g., changing electricity mixes to the selected country, based on the geographically closest available process in the agrifootprint background database
def create_new_agricultural_production_processes(crop_name,country_code_agriculture,closest_country,process_type,eidb_reg,afdb_reg):
    for activity in [act for act in afdb_reg if "custom_agricultural_process_" in act["code"] and process_type in act['name'] and crop_name in act['name'] and "Economic" in act['name'] and "market" not in act['name'] and country_code_agriculture in act['location']]:
        activity.delete()
    original_process = [act for act in afdb_reg if process_type in act['name'] and crop_name in act['name'] and "Economic" in act['name'] and "market" not in act['name'] and closest_country[-2:] in act['location']][0]      
    new_process = original_process.copy(code="custom_agricultural_process_"+process_type+"_"+crop_name+"_"+country_code_agriculture,location=country_code_agriculture)
    new_process.save()
    new_process["name"] = original_process["name"].replace(closest_country[-2:],country_code_agriculture)
    new_process["reference product"] = original_process["reference product"].replace(closest_country[-2:],country_code_agriculture)
    new_process.save()
    
    for exchange in new_process.exchanges():
        if exchange["type"] == "technosphere":
            exchange_input_temp = [act for act in eidb_reg if act['code'] == exchange["input"][1]]
            if exchange_input_temp == []:
                exchange_input = [act for act in afdb_reg if act['code'] == exchange["input"][1]][0]
                process_in_ecoinvent = False
            else:
                exchange_input = exchange_input_temp[0]
                process_in_ecoinvent = True
            if exchange_input["location"] == closest_country[-2:]:
                name = exchange["name"]
                amount = exchange["amount"]
                unit = exchange["unit"]
                type = exchange["type"]
                exchange.delete()
                if process_in_ecoinvent:
                    exchange_substitution_temp = [act for act in eidb_reg if act['name'] == name and country_code_agriculture in act['location']]
                    if exchange_substitution_temp == []:
                        raise ValueError(name + " not available for "+country_code_agriculture+".")
                    else:
                        exchange_substitution = exchange_substitution_temp[0]
                else:
                    name = exchange["name"].replace(closest_country[-2:],country_code_agriculture)
                    exchange_substitution = [act for act in afdb_reg if act['name'] == name and country_code_agriculture in act['location']][0]
                new_process.new_exchange(input=exchange_substitution.key, amount = amount, unit = unit, type = type).save()

    new_process.save()

def check_if_agricultural_activities_exist_and_create_them_if_not(country,crop_name,production_countries_pea_Europe,production_countries_soy_Europe,production_countries_wheat_Europe,distances_european_countries,eidb_reg,afdb_reg):
    test_activity = [act for act in afdb_reg if "start material" in act['name'] and crop_name in act['name'] and "Economic" in act['name'] and "market" not in act['name'] and country in act['location']]
    if test_activity == []:
        if crop_name == "Peas":
            closest_country = find_closest_production_country_to_create_new_production_processes(country,production_countries_pea_Europe,distances_european_countries)
        elif crop_name == "Soybeans":
            closest_country = find_closest_production_country_to_create_new_production_processes(country,production_countries_soy_Europe,distances_european_countries)
        else:
            closest_country = find_closest_production_country_to_create_new_production_processes(country,production_countries_wheat_Europe,distances_european_countries)
        print("Creating new agricultural activities for " + crop_name + " in " + country + " based on the example of " + closest_country + ".")

        create_new_agricultural_production_processes(crop_name,country,closest_country,"start material",eidb_reg,afdb_reg)
        if crop_name == "Peas":
            create_new_agricultural_production_processes(crop_name,country,closest_country,"dry, at farm",eidb_reg,afdb_reg)
        elif crop_name == "Wheat":
            create_new_agricultural_production_processes(crop_name,country,closest_country,"grain, at farm",eidb_reg,afdb_reg)
        else:
            create_new_agricultural_production_processes(crop_name,country,closest_country,"at farm",eidb_reg,afdb_reg)
        create_new_agricultural_production_processes(crop_name,country,closest_country,"dried",eidb_reg,afdb_reg)
    else:
        print("Agricultural activities for " + crop_name + " in " + country + " are already present.")

#Function that creates parameters with probability distributions
def create_params(name,distribution,minimum,maximum,mean,sd):
    if distribution == "TRIANGLE":
        param = agb.newFloatParam(
            name,
            default=float(mean),
            min=float(minimum), max=float(maximum),
            distrib=agb.DistributionType.TRIANGLE,
            description=name)
    elif distribution == "FIXED":
        param = agb.newFloatParam(
            name,
            default=float(mean),
            distrib=agb.DistributionType.FIXED,
            description=name)
    elif distribution == "NORMAL":
        param = agb.newFloatParam(
            name,
            default=float(mean),
            min=float(minimum), max=float(maximum), std=float(sd),
            distrib=agb.DistributionType.NORMAL,
            description=name)
    elif distribution == "LOGNORMAL":
        param = agb.newFloatParam(
            name,
            default=float(mean),
            std=float(sd),min=float(minimum),max=float(maximum),
            distrib=agb.DistributionType.LOGNORMAL,
            description=name)
    elif distribution == "UNIFORM":
        param = agb.newFloatParam(
            name,
            default=(float(minimum)+float(maximum))/2,
            std=float(sd),min=float(minimum),max=float(maximum),
            distrib=agb.DistributionType.LINEAR,
            description=name)
    else:
        raise ValueError("Selected distribution type doesn't exist.")


def calculate_transport_parameters(process_location, location_last_process, crop, european_countries, distances_european_countries, production_to_port_distance, transport_between_ports, europe_distance_from_port):
    transport_parameters = []

    transport_distance_data = {
            "Parameter values": [
                "Uncertainty type",
                "Amount",
                "loc",
                "scale",
                "shape",
                "minimum",
                "maximum"
            ],
            "Values": [
                "norm",
                np.nan,
                np.nan,
                np.nan,
                np.nan,
                0,
                np.nan
            ]
        }
    transport_distance_parameters = pd.DataFrame(transport_distance_data)
    transport_distance_parameters.set_index("Parameter values", inplace=True)
    transport_distance_parameters.index.name = None

    if isinEurope(process_location,european_countries) and isinEurope(location_last_process,european_countries):
        target_country_ids = {process_location,location_last_process}
        matching_row = distances_european_countries[distances_european_countries.apply(lambda row: {row["country1 ID"], row["country2 ID"]} == target_country_ids, axis=1)]

        transport_mode = "transport, freight, lorry, all sizes, EURO6 to generic market for transport, freight, lorry, unspecified" #EURO6 or lower??
        transport_location = "RER"
        transport_name = "transport_Europe"
        params_within_Europe = transport_distance_parameters.copy(deep=True)

        params_within_Europe.loc["Amount"] = float(matching_row.iloc[0]["mean"]) * 1.2 #Detour factor 1.2 to translate air distance to road distance
        params_within_Europe.loc["loc"] = float(matching_row.iloc[0]["mean"]) * 1.2
        params_within_Europe.loc["scale"] = float(matching_row.iloc[0]["std"]) * 1.2

        transport_parameters.append([transport_name,transport_mode,transport_location,params_within_Europe])
    else:
        transport_mode_origin = "transport, freight, lorry, all sizes, EURO6 to generic market for transport, freight, lorry, unspecified" #EURO6 or lower??
        transport_location_origin = "RoW"
        transport_name_origin = "transport_overseas_origin"
        params_origin = transport_distance_parameters.copy(deep=True)

        params_origin.loc["Amount"] = float(production_to_port_distance.loc[(production_to_port_distance["Crop"]==crop) & (production_to_port_distance["Country ID"]==location_last_process)]["mean"].iloc[0]) * 1.2 #Detour factor 1.2 to translate air distance to road distance
        params_origin.loc["loc"] = float(production_to_port_distance.loc[(production_to_port_distance["Crop"]==crop) & (production_to_port_distance["Country ID"]==location_last_process)]["mean"].iloc[0]) * 1.2
        params_origin.loc["scale"] = float(production_to_port_distance.loc[(production_to_port_distance["Crop"]==crop) & (production_to_port_distance["Country ID"]==location_last_process)]["sd"].iloc[0]) * 1.2

        transport_parameters.append([transport_name_origin,transport_mode_origin,transport_location_origin,params_origin])

        transport_mode_shipping = "market for transport, freight, sea, container ship"
        transport_location_shipping = "GLO"
        transport_name_shipping = "transport_overseas_shipping"
        params_shipping = transport_distance_parameters.copy(deep=True)

        params_shipping.loc["Amount"] = float(transport_between_ports.loc[(transport_between_ports["Crop"]==crop) & (transport_between_ports["Origin ID"]==location_last_process) & (transport_between_ports["Destination ID"]==process_location)]["Mean distance"].iloc[0])
        params_shipping.loc["loc"] = float(transport_between_ports.loc[(transport_between_ports["Crop"]==crop) & (transport_between_ports["Origin ID"]==location_last_process) & (transport_between_ports["Destination ID"]==process_location)]["Mean distance"].iloc[0])
        params_shipping.loc["scale"] = float(transport_between_ports.loc[(transport_between_ports["Crop"]==crop) & (transport_between_ports["Origin ID"]==location_last_process) & (transport_between_ports["Destination ID"]==process_location)]["Sd distance"].iloc[0])

        transport_parameters.append([transport_name_shipping,transport_mode_shipping,transport_location_shipping,params_shipping])

        transport_mode_destination = "transport, freight, lorry, all sizes, EURO6 to generic market for transport, freight, lorry, unspecified" #EURO6 or lower??
        transport_location_destination = "RER"
        transport_name_destination = "transport_overseas_destination"
        params_destination = transport_distance_parameters.copy(deep=True)

        params_destination.loc["Amount"] = float(europe_distance_from_port.loc[europe_distance_from_port["ID"]==process_location]["Mean dist"].iloc[0]) * 1.2 #Detour factor 1.2 to translate air distance to road distance
        params_destination.loc["loc"] = float(europe_distance_from_port.loc[europe_distance_from_port["ID"]==process_location]["Mean dist"].iloc[0]) * 1.2
        params_destination.loc["scale"] = float(europe_distance_from_port.loc[europe_distance_from_port["ID"]==process_location]["Sd dist"].iloc[0]) * 1.2
       
        transport_parameters.append([transport_name_destination,transport_mode_destination,transport_location_destination,params_destination])
        
    #print(transport_parameters)
    return transport_parameters

def calculate_results_process_contribution(LCIA_results_contribution_temp,LCIA_results_electricity_protein_separation,LCIA_results_heat_protein_separation,formulas,transport,LCIA_parameters,n_iter):
    LCIA_results_contribution = {}
    for process in formulas["Process"].unique():
        if process == "crop":
            for impact_category in LCIA_results_contribution_temp[process].columns:
                LCIA_results_contribution[f"{process} - {impact_category}"] = LCIA_results_contribution_temp[process][impact_category]
        elif process in transport:
            for impact_category in LCIA_results_contribution_temp[process].columns:
                LCIA_results_contribution[f"{process} - {impact_category}"] = LCIA_results_contribution_temp[process][impact_category] - LCIA_results_contribution_temp[previous_process][impact_category] - LCIA_results_contribution_temp[f"Transport_to_{process}"][impact_category]
        else:
            for impact_category in LCIA_results_contribution_temp[process].columns:
                LCIA_results_contribution[f"{process} - {impact_category}"] = LCIA_results_contribution_temp[process][impact_category] - LCIA_results_contribution_temp[previous_process][impact_category]
        previous_process = process

    for impact_category in LCIA_results_contribution_temp[process].columns:
        LCIA_results_contribution[f"{formulas["Process"].unique()[-1]} - {impact_category}"] = LCIA_results_contribution[f"{formulas["Process"].unique()[-1]} - {impact_category}"] - LCIA_results_electricity_protein_separation[impact_category] - LCIA_results_heat_protein_separation[impact_category]
        LCIA_results_contribution[f"Heat_protein_separation - {impact_category}"] = LCIA_results_heat_protein_separation[impact_category]
        LCIA_results_contribution[f"Electricity_protein_separation - {impact_category}"] = LCIA_results_electricity_protein_separation[impact_category]

    first = "yes"
    for transport_process in transport:
        if first == "yes":
            for impact_category in LCIA_results_contribution_temp[process].columns:
                LCIA_results_contribution[f"Transport - {impact_category}"] = LCIA_results_contribution_temp[f"Transport_to_{transport_process}"][impact_category]
            first = "no"
        else:
            for impact_category in LCIA_results_contribution_temp[process].columns:
                LCIA_results_contribution[f"Transport - {impact_category}"] = LCIA_results_contribution[f"Transport - {impact_category}"] + LCIA_results_contribution_temp[f"Transport_to_{transport_process}"][impact_category]

    LCIA_results_contribution = pd.DataFrame.from_dict(LCIA_results_contribution)
    LCIA_results_contribution_protein = LCIA_results_contribution.copy()
    for i in range(n_iter):
        protein_content = LCIA_parameters.loc[LCIA_parameters.index.str.contains("protein_out"),f"value_{i+1}"].iloc[0]
        LCIA_results_contribution_protein.iloc[i] = LCIA_results_contribution_protein.iloc[i] / protein_content

    return LCIA_results_contribution, LCIA_results_contribution_protein
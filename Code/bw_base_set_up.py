import bw2data as bd
from bw2io.utils import activity_hash
import pandas as pd
from copy import deepcopy
import os
import re
import bw2io as bi

from name_match import get_lca_db_locations
from lcia_regionalized_cfs import biodiversity_cf_match_locations, calculate_area_weighted_regional_water_cfs

project = "Parametrized LCA"
bd.projects.set_current(project)
bio3 = bd.Database("ecoinvent-3.10-biosphere")

def get_image_region(location,conversion_list):
    if location in list(conversion_list["shortname"]):
        image_region = conversion_list.loc[conversion_list["shortname"] == location, "IMAGE Region"].iloc[0]
    else:
        raise KeyError(f"{location} not found in the conversion list from ecoinvent to IMAGE regions.")
    
    return image_region

# start with biomass_base project, with ecoinvent-3.10-biosphere and ecoinvent-3.10-cutoff
def bw_generate_new_biosphere_data_water(bio_act_list, new_bio_name):
    loc_list = get_lca_db_locations()
    biosphere_data = {}
    for bio_act in bio_act_list:
        for loc in loc_list:
            #print(bio_act, loc)
            bio_act_data = deepcopy(bio_act.as_dict())
            bio_act_data['location'] = loc  # Add location
            bio_act_data['database'] = new_bio_name
            bio_act_code = activity_hash(bio_act_data)
            bio_act_data['code'] = bio_act_code
            dbname_code = (new_bio_name, bio_act_code)
            biosphere_data[dbname_code] = bio_act_data
            bio_act_data_irri = deepcopy(bio_act.as_dict())
            bio_act_data_irri['location'] = loc  # Add location
            bio_act_data_irri['database'] = new_bio_name
            bio_act_data_irri['name'] = f'{bio_act.get("name")}, irrigation'
            bio_act_code_irri = activity_hash(bio_act_data_irri)
            bio_act_data_irri['code'] = bio_act_code_irri
            dbname_code_irri = (new_bio_name, bio_act_code_irri)
            biosphere_data[dbname_code_irri] = bio_act_data_irri
    return biosphere_data

def bw_add_lcia_method_aware():
    flows_list = []
    if os.path.exists(r'data_regionalized_impact_assessment/interim/cf_aware_processed.csv'):
        df = pd.read_csv(r'data_regionalized_impact_assessment/interim/cf_aware_processed.csv',encoding="latin1", sep = ";")
        df = df.map(lambda x: x.replace('__', ',') if isinstance(x, str) else x)
        df = df.drop("Column1",axis=1)
        df['Location'] = df['Location'].fillna('NA')
    else:
        df = calculate_area_weighted_regional_water_cfs()
    new_bio_db = bd.Database('biosphere water regionalized')
    for flow in new_bio_db:
        loc = flow.get('location')
        if 'irrigation' in flow.get('name'):
            cf = df.loc[df.Location == loc, 'Agg_CF_irri'].iloc[0]
        else:
            cf = df.loc[df.Location == loc, 'Agg_CF_non_irri'].iloc[0]
        if 'water' in flow.get('categories'):
            cf *= -1
        flows_list.append([flow.key, cf])
    aware_tuple = ('AWARE regionalized', 'Water stress', 'Annual')
    aware_method = bd.Method(aware_tuple)
    aware_data = {'unit': 'm3 world',
                  'num_cfs': len(flows_list),
                  'description': 'AWARE'}
    aware_method.validate(flows_list)
    aware_method.register(**aware_data)
    aware_method.write(flows_list)

def bw_generate_new_biosphere_data_luluc(bio_act_list, new_bio_name):
    loc_list = get_lca_db_locations()
    biosphere_data = {}
    for bio_act in bio_act_list:
        for loc in loc_list:
            # print(bio_act, loc)
            bio_act_data = deepcopy(bio_act.as_dict())
            bio_act_data['location'] = loc  # Add location
            bio_act_data['database'] = new_bio_name
            bio_act_code = activity_hash(bio_act_data)
            bio_act_data['code'] = bio_act_code
            dbname_code = (new_bio_name, bio_act_code)
            biosphere_data[dbname_code] = bio_act_data
    bio_act_additional_list = [x for x in bio3 if 'annual crop, irrigated, intensive' in x.get('name')]
    intensity_list = ['intensive', 'extensive', 'minimal']
    loc_list = get_lca_db_locations()
    for bio_act in bio_act_additional_list:
        for intensity in intensity_list:
            bio_act_name = f'{bio_act.get("name").split(", ")[0]}, {bio_act.get("name").split(", ")[1]}, {intensity}'
            for loc in loc_list:
                bio_act_data = deepcopy(bio_act.as_dict())
                bio_act_data['location'] = loc  # Add location
                bio_act_data['name'] = bio_act_name
                bio_act_data['database'] = new_bio_name
                bio_act_code = activity_hash(bio_act_data)
                bio_act_data['code'] = bio_act_code
                dbname_code = (new_bio_name, bio_act_code)
                biosphere_data[dbname_code] = bio_act_data
    return biosphere_data


def bw_add_lcia_method_biodiversity():
    flows_occ_list = []
    flows_tra_list = []
    if os.path.exists(r'data_regionalized_impact_assessment/interim/cf_biodiversity_processed_new.csv'):
        df = pd.read_csv(r'data_regionalized_impact_assessment/interim/cf_biodiversity_processed_new.csv', encoding="latin1", sep=";", index_col=0)
        df.index.name = None
        df = df.map(lambda x: x.replace('__', ',') if isinstance(x, str) else x)
        df['Location'] = df['Location'].fillna('NA')
    else:
        df = biodiversity_cf_match_locations()
    new_bio_db = bd.Database('biosphere luluc regionalized')
    df_loc = pd.read_csv(r'data_regionalized_impact_assessment/external/Scherer_land_use_match.csv')
    df_check = pd.DataFrame()
    for flow in new_bio_db:
        loc = flow.get('location')
        flow_name = flow.get('name').replace(',', '')
        index_nr = df_loc.where(df_loc == flow_name).dropna(how='all').index
        if index_nr.shape[0] > 0:
            lu_type = df_loc.loc[index_nr, 'Land use type'].values[0]
            lu_intensity = df_loc.loc[index_nr, 'Land use intensity'].values[0]
            habitat = f'{lu_type}_{lu_intensity}'
            try:
                if 'Occupation' in flow_name:
                    cf = df.loc[(df.Location == loc) & (df.habitat == habitat), 'CF_occ_avg_glo'].iloc[0]
                    flows_occ_list.append([flow.key, cf])
                elif 'Transformation from' in flow_name:
                    cf = -df.loc[(df.Location == loc) & (df.habitat == habitat), 'CF_tra_avg_glo'].iloc[0]
                    flows_tra_list.append([flow.key, cf])
                elif 'Transformation to' in flow_name:
                    cf = df.loc[(df.Location == loc) & (df.habitat == habitat), 'CF_tra_avg_glo'].iloc[0]
                    flows_tra_list.append([flow.key, cf])
            except:
                df_temp = pd.DataFrame([[loc, habitat]], columns=['location', 'habitat'])
                df_check = pd.concat([df_check, df_temp], ignore_index=True)
    occ_tuple = ('Biodiversity regionalized', 'Occupation', 'Biodiversity loss (LUBL)')
    occ_method = bd.Method(occ_tuple)
    occ_data = {'unit': 'PDF*year/m2a',
                'num_cfs': len(flows_occ_list),
                'description': 'method based on new GLAM Initiative'}
    occ_method.validate(flows_occ_list)
    occ_method.register(**occ_data)
    occ_method.write(flows_occ_list)
    tra_tuple = ('Biodiversity regionalized', 'Transformation', 'Biodiversity loss (LUBL)')
    tra_method = bd.Method(tra_tuple)
    tra_data = {'unit': 'PDF*year/m2',
                'num_cfs': len(flows_tra_list),
                'description': 'method based on new GLAM Initiative'}
    tra_method.validate(flows_tra_list)
    tra_method.register(**tra_data)
    tra_method.write(flows_tra_list)

def bw_generate_new_biosphere_data_pm(bio_act_list, new_bio_name):
    loc_list = get_lca_db_locations()
    biosphere_data = {}
    for bio_act in bio_act_list:
        for loc in loc_list:
            bio_act_data_general = deepcopy(bio_act.as_dict())
            bio_act_data_general['location'] = loc  # Add location
            bio_act_data_general['database'] = new_bio_name
            bio_act_data_general['name'] = f'{bio_act.get("name")}, general'
            bio_act_code_general = activity_hash(bio_act_data_general)
            bio_act_data_general['code'] = bio_act_code_general
            dbname_code_general = (new_bio_name, bio_act_code_general)
            biosphere_data[dbname_code_general] = bio_act_data_general

            bio_act_data_chemical = deepcopy(bio_act.as_dict())
            bio_act_data_chemical['location'] = loc  # Add location
            bio_act_data_chemical['database'] = new_bio_name
            bio_act_data_chemical['name'] = f'{bio_act.get("name")}, chemical'
            bio_act_code_chemical = activity_hash(bio_act_data_chemical)
            bio_act_data_chemical['code'] = bio_act_code_chemical
            dbname_code_chemical = (new_bio_name, bio_act_code_chemical)
            biosphere_data[dbname_code_chemical] = bio_act_data_chemical

            bio_act_data_energy = deepcopy(bio_act.as_dict())
            bio_act_data_energy['location'] = loc  # Add location
            bio_act_data_energy['database'] = new_bio_name
            bio_act_data_energy['name'] = f'{bio_act.get("name")}, energy'
            bio_act_code_energy = activity_hash(bio_act_data_energy)
            bio_act_data_energy['code'] = bio_act_code_energy
            dbname_code_energy = (new_bio_name, bio_act_code_energy)
            biosphere_data[dbname_code_energy] = bio_act_data_energy

            bio_act_data_agricultural_soil = deepcopy(bio_act.as_dict())
            bio_act_data_agricultural_soil['location'] = loc  # Add location
            bio_act_data_agricultural_soil['database'] = new_bio_name
            bio_act_data_agricultural_soil['name'] = f'{bio_act.get("name")}, agricultural_soil'
            bio_act_code_agricultural_soil = activity_hash(bio_act_data_agricultural_soil)
            bio_act_data_agricultural_soil['code'] = bio_act_code_agricultural_soil
            dbname_code_agricultural_soil = (new_bio_name, bio_act_code_agricultural_soil)
            biosphere_data[dbname_code_agricultural_soil] = bio_act_data_agricultural_soil

    return biosphere_data

def bw_add_lcia_method_pm():
    flows_list = []
    df = pd.read_csv(r'data_regionalized_impact_assessment/interim/cf_pm_image_regions.csv', sep = ";")
    df = df.fillna(0)
    eidb_310_to_image_conversion = pd.read_csv(r'data_regionalized_impact_assessment/interim/Ecoinvent_310_to_IMAGE_conversion.csv', encoding="latin1",sep=";", keep_default_na=False)
    eidb_310_to_image_conversion = eidb_310_to_image_conversion.map(lambda x: x.replace('__', ',') if isinstance(x, str) else x)
    new_bio_db = bd.Database(f'biosphere pm regionalized')
    for flow in new_bio_db:
        loc = flow.get('location')
        image_region = get_image_region(loc,eidb_310_to_image_conversion)
        sector = flow.get('name').split()[-1]
        if 'Particulate Matter, <' in flow.get('name'):
            cf = df.loc[df.Region == image_region, f'CF_PM2.5_{sector}_DALY_per_kg'].iloc[0]
        elif 'Sulfur dioxide' in flow.get('name'):
            cf = df.loc[df.Region == image_region, f'CF_SO2_{sector}_DALY_per_kg'].iloc[0]
        elif 'Nitrogen oxides' in flow.get('name'):
            cf = df.loc[df.Region == image_region, f'CF_NOx_{sector}_DALY_per_kg'].iloc[0]
        elif 'Ammonia' in flow.get('name'):
            cf = df.loc[df.Region == image_region, f'CF_NH3_{sector}_DALY_per_kg'].iloc[0]
        flows_list.append([flow.key, cf])

    pm_tuple = ('PM regionalized', 'Particulate matter', 'health impacts (PMHI)')
    pm_method = bd.Method(pm_tuple)
    pm_data = {'unit': 'DALY',
                  'num_cfs': len(flows_list),
                  'description': f'method based on CFs of Oberschelp et al. (2020)'}
    pm_method.validate(flows_list)
    pm_method.register(**pm_data)
    pm_method.write(flows_list)

def bw_add_lcia_method_ipcc_ar6():
    df = pd.read_excel(r'data_regionalized_impact_assessment/raw_data/ghg_cfs_ipcc_ar6.xlsx', engine='openpyxl', sheet_name='CFs')
    for cf in ['GWP_100a', 'GTP_100a']:
        for cf_type in ['all', 'Biogenic', 'Fossil', 'LUC']:
            flows_list = []
            if cf_type != 'all':
                df1 = df.loc[df.Type == cf_type]
            else:
                df1 = df.copy()
            for flow in bio3:
                if flow['name'] in list(df1.Gas.unique()):
                    cf_val = df1.loc[df1.Gas == flow['name'], cf].iloc[0]
                    flows_list.append([flow.key, cf_val])
            ipcc_tuple = ('IPCC_AR6', cf, cf_type)
            ipcc_method = bd.Method(ipcc_tuple)
            ipcc_data = {'unit': 'CO2-eq',
                         'num_cfs': len(flows_list),
                         'description': 'ipcc ar6 cf'}
            ipcc_method.validate(flows_list)
            ipcc_method.register(**ipcc_data)
            ipcc_method.write(flows_list)


def bw_set_up():
    # regionalized biosphere for land occupation and transformation
    luluc_name = "biosphere luluc regionalized"
    water_name = "biosphere water regionalized"
    pm_name = "biosphere pm regionalized"
    # del bd.databases[water_name]
    # del bd.databases[luluc_name]
    if luluc_name in bd.databases:
        print(f'Regionalized land use and land use change biosphere database: "{luluc_name}" already exist. No set up '
              f'required.')
    else:
        print(f'Setting up regionalized land use and land use change biosphere database: "{luluc_name}".')
        luluc_list = [act for act in bio3 if ("occupation" in act['name'].lower()
                                             or 'transformation' in act['name'].lower())
                      and 'non-use' not in act['name']
                      and 'obsolete' not in act['name']]
        biosphere_luluc_data = bw_generate_new_biosphere_data_luluc(luluc_list, luluc_name)
        new_bio_db = bd.Database(luluc_name)
        new_bio_db.write(biosphere_luluc_data)
    if water_name in bd.databases:
        print(f'Regionalized water biosphere database: "{water_name}" already exist. No set up required.')
    else:
        print(f'Setting up regionalized water biosphere database: "{water_name}".')
        water_use_list = [act for act in bio3 if "Water" in act['name']
                          and 'natural resource' in act['categories']
                          and 'air' not in act['name']
                          and 'ocean' not in act['name']
                          and 'ocean' not in act.get('categories')]
        water_emission_list = [act for act in bio3 if "Water" in act['name']
                               and 'water' in act['categories']
                               and 'ocean' not in act.get('categories')]
        water_list = water_use_list + water_emission_list
        biosphere_water_data = bw_generate_new_biosphere_data_water(water_list, water_name)
        new_bio_db = bd.Database(water_name)
        new_bio_db.write(biosphere_water_data)
    if pm_name in bd.databases:
        print(f'Regionalized particulate matter biosphere database: "{pm_name}" already exist. No set up required.')
    else:
        print(f'Setting up regionalized particulate matter biosphere database: "{pm_name}".')
        pm25_and_precursor_list = [act for act in bio3 if "Particulate Matter, <" in act["name"]
                                    or "Sulfur dioxide" in act["name"]
                                    or "Nitrogen oxides" in act["name"]
                                    or "Ammonia" in act["name"]]
        biosphere_pm_data = bw_generate_new_biosphere_data_pm(pm25_and_precursor_list, pm_name)
        new_bio_db = bd.Database(pm_name)
        new_bio_db.write(biosphere_pm_data)
    if ('Biodiversity regionalized', 'Occupation', 'Biodiversity loss (LUBL)') in list(bd.methods):
        print('Regionalized biodiversity impact assessment methods already set up.')
    else:
        print('Setting up regionalized biodiversity impact assessment methods')
        bw_add_lcia_method_biodiversity()
    if ('AWARE regionalized', 'Water stress', 'Annual') in list(bd.methods):
        print('Regionalized AWARE impact assessment methods already set up.')
    else:
        print('Setting up regionalized AWARE impact assessment methods')
        bw_add_lcia_method_aware()
    if ('PM regionalized', 'Particulate matter', 'health impacts (PMHI)') in list(bd.methods):
        print('Regionalized PM impact assessment methods already set up.')
    else:
        print('Setting up regionalized PM impact assessment methods')
        bw_add_lcia_method_pm()
    if ('IPCC_AR6', 'GWP_100a', 'all') in list(bd.methods):
        print('IPCC AR6 impact assessment methods already set up.')
    else:
        print('Setting up IPCC AR6 impact assessment methods')
        bw_add_lcia_method_ipcc_ar6()

def check_if_act_is_agri(act):
    agri_yes_no = 0
    if 'simapro metadata' in act.as_dict().keys():
        if 'blue water' in act.get('simapro metadata').get('Comment'):
            agri_yes_no += 1
    if 'Farming and supply' in act.get('name'):
        agri_yes_no += 1
    if 'classifications' in act.as_dict().keys():
        for i in act.get('classifications'):
            if i[0] == 'ISIC rev.4 ecoinvent':
                if (
                        ('011' in i[1] or '012' in i[1])
                        and '201' not in i[1]
                        and '301' not in i[1]
                ):
                    agri_yes_no += 1
            elif i[1] == 'agricultural production/plant production':
                agri_yes_no += 1
    return agri_yes_no

def get_process_category(act):
    chemical_activities_list = ["2011","1920","2021","2012","2023","2029","2022","202","20","201"]
    energy_activities_list = ["3510","3530","3520","35"]
    agriculture_activities_list = ["0161","0111","0113","1080","0119","0163","0130","0116","0122","0127","0162","0123","0124","0125","0128","0126","0145","0112","0129","0144","0114","0121","0146","0149"]

    if act.get("classifications"):
        for classification in act.get("classifications"):
            if 'ISIC rev.4 ecoinvent' in classification[0]:
                category_number = classification[1].split(":")[0]
        if category_number in chemical_activities_list:
            process_category = "chemical"
        elif category_number in energy_activities_list:
            process_category = "energy"
        elif category_number in agriculture_activities_list:
            process_category = "agricultural"
        elif category_number:
            process_category = "general"
        else:
            process_category = "No category found!"
    else:
        if act.get("simapro metadata").get("Category type") == "energy":
            process_category = "energy"
        elif "at farm" in act["name"]:
            process_category = "agricultural"
        elif "at plant" in act["name"]:
            process_category = "chemical"
        else:
            process_category = "general"

    return process_category

def regionalize_db(db_name):
    regionalized_db_name = f'{db_name}_regionalized'
    if regionalized_db_name in list(bd.databases):
        print(f'{regionalized_db_name} already exist. No need to copy from {db_name}.')
    else:
        print(f'start copying {db_name} to {regionalized_db_name}.')
        bd.Database(db_name).copy(regionalized_db_name)
        bio = bd.Database("ecoinvent-3.10-biosphere")
        db_to_regionalize = bd.Database(regionalized_db_name)
        new_bio_db_luc = bd.Database('biosphere luluc regionalized')
        new_bio_db_water = bd.Database('biosphere water regionalized')
        new_bio_db_pm = bd.Database('biosphere pm regionalized')

        # flag_db = ei.metadata.get("regionalized", False)
        # if not flag_db:
        print('start regionalizing water and land flows')
        water_use_list = [act for act in bio if "Water" in act['name']
                          and 'natural resource' in act['categories']
                          and 'air' not in act['name']
                          and 'ocean' not in act['name']
                          and 'ocean' not in act.get('categories')]
        water_emission_list = [act for act in bio if "Water" in act['name']
                               and 'water' in act['categories']
                               and 'ocean' not in act.get('categories')]
        water_list = water_use_list + water_emission_list
        luluc_list = [act for act in bio if ("occupation" in act['name'].lower()
                                             or 'transformation' in act['name'].lower())
                      and 'non-use' not in act['name']
                      and 'obsolete' not in act['name']]
        pm25_and_precursor_list = [act for act in bio if "Particulate Matter, <" in act["name"]
                                    or "Sulfur dioxide" in act["name"]
                                    or "Nitrogen oxides" in act["name"]
                                    or "Ammonia" in act["name"]]
        i = 0
        for act in db_to_regionalize:
            if 'Copied from ecoinvent' not in act.get('name') and \
                    'Evonik' not in act.get('name') and \
                    'Emulsifier, proxy' not in act.get('name'):
                if 'agrifootprint' in db_name:
                    location_pattern = r"\{(.*?)\}"
                    match = re.findall(pattern=location_pattern, string=act['name'])
                    location = match[0]
                else:
                    location = act['location']
                i += 1
                if i % 100 == 0:
                    print(f'updated {str(i)} activities')
                agri_yes_no = check_if_act_is_agri(act)
                for exc in act.exchanges():
                    if exc.input in water_list:
                        flag_replaced = exc.get("replaced with regionalized", False)
                        if not flag_replaced:
                            data = deepcopy(exc.as_dict())
                            try:
                                data.pop('flow')
                            except:
                                pass
                            if agri_yes_no >= 1:
                                exc_name = exc.input['name'] + ', irrigation'
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_water if
                                    bio_act['name'] == exc_name and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                                data['name'] += ', irrigation'
                            else:
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_water if
                                    bio_act['name'] == exc.input['name'] and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                            if not len(bio_act_regionalized) == 1:
                                print(bio_act_regionalized)
                                print(exc)
                            assert len(bio_act_regionalized) == 1
                            bio_act_regionalized = bio_act_regionalized[0]
                            data['input'] = (bio_act_regionalized['database'], bio_act_regionalized['code'])
                            act.new_exchange(**data).save()
                            exc['amount'] = 0
                            exc['replaced with regionalized'] = True
                            exc.save()
                    elif exc.input in luluc_list:
                        flag_replaced = exc.get("replaced with regionalized", False)
                        if not flag_replaced:
                            data = deepcopy(exc.as_dict())
                            try:
                                data.pop('flow')
                            except:
                                pass
                            bio_act_regionalized = [
                                bio_act for bio_act in new_bio_db_luc if
                                bio_act['name'] == exc.input['name'] and
                                bio_act['categories'] == exc.input['categories'] and
                                bio_act['location'] == location
                            ]
                            if not len(bio_act_regionalized) == 1:
                                print(bio_act_regionalized)
                                print(exc)
                            assert len(bio_act_regionalized) == 1
                            bio_act_regionalized = bio_act_regionalized[0]
                            data['input'] = (bio_act_regionalized['database'], bio_act_regionalized['code'])
                            act.new_exchange(**data).save()
                            exc['amount'] = 0
                            exc['replaced with regionalized'] = True
                            exc.save()
                    elif exc.input in pm25_and_precursor_list:
                        flag_replaced = exc.get("replaced with regionalized", False)
                        if not flag_replaced:
                            data = deepcopy(exc.as_dict())
                            try:
                                data.pop('flow')
                            except:
                                pass
                            process_category = get_process_category(act)
                            if process_category == "agricultural" and "Sulfur dioxide" in exc.input['name']:
                                process_category = "general"
                            if process_category == "chemical":
                                exc_name = exc.input['name'] + ', chemical'
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_pm if
                                    bio_act['name'] == exc_name and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                                data['name'] += ', chemical'
                            elif process_category == "energy":
                                exc_name = exc.input['name'] + ', energy'
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_pm if
                                    bio_act['name'] == exc_name and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                                data['name'] += ', energy'
                            elif process_category == "agricultural":
                                exc_name = exc.input['name'] + ', agricultural_soil'
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_pm if
                                    bio_act['name'] == exc_name and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                                data['name'] += ', agricultural_soil'
                            else:
                                exc_name = exc.input['name'] + ', general'
                                bio_act_regionalized = [
                                    bio_act for bio_act in new_bio_db_pm if
                                    bio_act['name'] == exc_name and
                                    bio_act['categories'] == exc.input['categories'] and
                                    bio_act['location'] == location
                                ]
                                data['name'] += ', general'
                            if not len(bio_act_regionalized) == 1:
                                print(bio_act_regionalized)
                                print(exc)
                            assert len(bio_act_regionalized) == 1
                            bio_act_regionalized = bio_act_regionalized[0]
                            data['input'] = (bio_act_regionalized['database'], bio_act_regionalized['code'])
                            act.new_exchange(**data).save()
                            exc['amount'] = 0
                            exc['replaced with regionalized'] = True
                            exc.save()
            # ei.metadata["regionalized"] = True
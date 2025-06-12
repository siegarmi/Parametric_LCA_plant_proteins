import pandas as pd
import bw2data as bd
import math


def get_country_match_df():
    df_country = pd.read_excel(r'data_regionalized_impact_assessment/raw_data/Country.xlsx', engine='openpyxl', sheet_name='Sheet1')
    df_country.loc[df_country.Country == "Namibia", "ISO2"] = "NA"
    return df_country


def get_country_match_df_globiom():
    df_country = get_country_match_df()
    df_country_unique = df_country.drop_duplicates(subset='GLOBIOM', keep='first')
    return df_country_unique


def get_country_match_df_fra():
    df_country = get_country_match_df()
    df_country_unique = df_country.drop_duplicates(subset='FRA', keep='first')
    return df_country_unique


def get_country_match_globiom_fpe():
    df_country = get_country_match_df()
    df_country_unique = df_country.drop_duplicates(subset='GLOBIOM_region_FPE2021', keep='first')
    return df_country_unique


def get_country_match_df_aware():
    df_country = get_country_match_df()
    df_country_unique = df_country.drop_duplicates(subset='AWARE', keep='first')
    return df_country_unique


crop_globiom_list = ['Barl', 'Corn', 'Rape', 'Rice', 'Srgh', 'Soya', 'SugC', 'Whea']
crop_list = ['Barley grain', 'Maize', 'Rapeseed', 'Rice', 'Sorghum grain',
             'Soybeans', 'Sugar cane', 'Wheat grain']
residue_list = ['Barley straw', 'Maize stover', 'Rapeseed straw', 'Rice straw', 'Sorghum straw',
                'Soybean straw', 'Sugarcane tops and leaves', 'Wheat straw']
residue_list_short = ['Forest residues', 'Maize stover', 'Rice straw',
                      'Sugarcane tops and leaves', 'Wheat straw', 'Other agricultural residues']
crop_dict = {crop_globiom_list[i]: crop_list[i] for i in range(len(crop_list))}
crop_residue_dict = {residue_list[i]: crop_list[i] for i in range(len(crop_list))}
residue_crop_dict = {crop_list[i]: residue_list[i] for i in range(len(crop_list))}


def get_lca_db_locations():
    df_loc = pd.read_csv(r'data_regionalized_impact_assessment/raw_data/Locations_in_lca_db_new.csv', encoding="latin1",sep=";")
    df_loc = df_loc.drop("Column1", axis=1)
    df_loc = df_loc.map(lambda x: x.replace('__', ',') if isinstance(x, str) else x)
    df_country = get_country_match_df()
    afdb_region_list = list(df_country.AFDB_region.unique())
    image_region_list = list(df_country.IMAGE_region.unique())
    df_loc = df_loc.fillna('NA')
    loc_list = df_loc['Location'].to_list()
    append_list_afdb = [x for x in afdb_region_list if (x not in loc_list) and (pd.isnull(x) == False)]
    loc_list = loc_list + append_list_afdb
    append_list_image = [x for x in image_region_list if (x not in loc_list) and (pd.isnull(x) == False)]
    loc_list = loc_list + append_list_image
    return loc_list


lca_loc_dict = {'US only': 'US',
                'UN-OCEANIA': 'OCE',
                'APAC': 'RAS',
                'RER w/o RU': 'RER',
                'North America without Quebec': 'RNA',
                'IAI Area, EU27 & EFTA': 'RER',
                'IAI Area, Russia & RER w/o EU27 & EFTA': 'RER',
                'SS': 'SD',
                'IAI Area, Gulf Cooperation Council': 'RME',
                'TW': 'CN',
                'IAI Area, North America': 'RNA',
                'IAI Area, Asia, without China and GCC': 'RAS',
                'IAI Area, South America': 'RLA',
                'IAI Area, Africa': 'RAF',
                'UCTE': 'RER',
                'GI': 'ES',
                'Europe, without Russia and Türkiye': 'RER',
                'Canada without Quebec': 'CA',
                'XK': 'RS',
                'NORDEL': 'RER',
                'RER w/o DE+NL+RU': 'RER',
                'RER w/o CH+DE': 'RER',
                'ENTSO-E': 'RER',
                'CW': 'PR',
                'UN-SEASIA': 'SEAS',
                'HK': 'CN',
                'WECC': 'RNA',
                'CENTREL': 'RER',
                'Europe without Austria': 'RER',
                'Europe without Switzerland and Austria': 'RER',
                'UCTE without Germany': 'RER',
                'RoE': 'RER',
                'RoW': 'GLO',
                'World': 'GLO'}

luluc_list = [  # 'Transformation, from forest, primary (non-use)',
    'Transformation, from forest, extensive',
    'Transformation, from forest, intensive',
    'Transformation, from shrub land, sclerophyllous',
    'Transformation, from grassland, natural, for livestock grazing',
    'Transformation, from annual crop, intensive',
    'Transformation, from annual crop, extensive',
    'Transformation, from annual crop, minimal',
    'Transformation, to annual crop, intensive',
    'Transformation, to annual crop, extensive',
    'Transformation, to annual crop, minimal',
    'Transformation, to forest, extensive',
    'Transformation, to forest, intensive',
    'Transformation, to shrub land, sclerophyllous',
    'Occupation, annual crop, intensive',
    'Occupation, annual crop, extensive',
    'Occupation, annual crop, minimal',
    'Occupation, forest, intensive',
    'Occupation, forest, extensive',
    'Occupation, shrub land, sclerophyllous']


def get_luc_dict():
    bio_luc = bd.Database("biosphere luluc regionalized")
    luc_dict = {}
    for act in bio_luc:
        act_id = (act.get('database'), act.get('code'))
        act_name = act.get('name')
        if act_name in luc_dict.keys():
            luc_dict.get(act_name).update({act.get('location'): act_id})
        else:
            luc_dict.update({act.get('name'): {act.get('location'): act_id}})
    return luc_dict


sawmill_product_list = ['Sawnwood', 'Bark', 'Sawdust', 'WoodChips']
wood_harvest_list = ['FW_Biomass', 'LoggingResidues', 'OW_Biomass', 'PW_Biomass', 'SW_Biomass']

regionalized_act = ['transport, freight, lorry, unspecified, long haul',
                    'market for diesel, low-sulfur',
                    'transport, freight, lorry, unspecified, regional delivery',
                    'market for diesel, burned in building machine',
                    'diesel, burned in building machine',
                    'market group for electricity, medium voltage']

product_list = ['Forest residues', 'Maize stover', 'Rice straw', 'Sugarcane tops and leaves', 'Wheat straw']
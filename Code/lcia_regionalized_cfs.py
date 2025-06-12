import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats

from name_match import (get_country_match_df, get_country_match_df_globiom, get_country_match_df_aware,
                                  get_lca_db_locations, lca_loc_dict)


def calculate_area_per_country_and_land_use():
    lu_shape = gpd.read_file("data_regionalized_impact_assessment/external/shapefiles/LUID_CTY/LUID_CTY.shp")
    lu_shape = lu_shape.rename(columns={"Field2": "COUNTRY", "Field1_1": "LU_GRID"})
    land_use_map = r"data_regionalized_impact_assessment/external/GLAM_land_intensity_5min.tif"
    lu_c = lu_shape.dissolve(by='COUNTRY')
    lu_c.reset_index(inplace=True)
    lu_c = lu_c.drop(['LU_GRID'], axis=1)
    zs_land_use = zonal_stats(lu_c, land_use_map, categorical=True)
    nr_code = list(range(1, 17))
    df_land_use_area = lu_c.copy()
    df_land_use_area[nr_code] = 0
    for j in range(0, len(zs_land_use)):
        for i in nr_code:
            x = zs_land_use[j].get(i)
            df_land_use_area.iloc[j, i+1] = x
    df_land_use_area = df_land_use_area.fillna(0)
    df_land_use_area.iloc[:, 2:] = df_land_use_area.iloc[:, 2:].apply(lambda y: y / y.sum(), axis=1)
    temp = df_land_use_area.iloc[:, 2:].reindex(sorted(df_land_use_area.iloc[:, 2:].columns), axis=1)
    df_land_use_area = pd.concat([df_land_use_area.iloc[:, :2], temp], axis=1)
    df_land_use_area['country_area_km2'] = df_land_use_area['geometry'].to_crs(3395).map(lambda p: p.area / 10 ** 6)
    for x in nr_code:
        df_land_use_area[x] = df_land_use_area[x] * df_land_use_area['country_area_km2']
    return df_land_use_area


def calculate_area_weighted_regional_biodiversity_cfs():
    cf_o = pd.read_csv(r'data_regionalized_impact_assessment/external/biodiversity_CF_country_domain.csv', encoding='ISO-8859-1')
    df_country = get_country_match_df()
    df_country_globiom = get_country_match_df_globiom()
    df_area = calculate_area_per_country_and_land_use()
    df_cf = cf_o.copy()
    df_cf['Country'] = df_cf['iso3cd'].map(df_country.set_index('ISO3')['ISO2']).copy()
    df_cf = df_cf.dropna(subset=['Country'])
    df_area['Country'] = df_area['COUNTRY'].map(df_country_globiom.set_index('GLOBIOM')['ISO2']).copy()
    df_cf = df_cf[df_cf.Country.isin(list(df_area['Country'].unique()))]
    for x in df_cf.index:
        country = df_cf.loc[x, 'Country']
        hab_id = df_cf.loc[x, 'habitat_id']
        area = df_area.loc[df_area.Country == country, hab_id].iloc[0]
        df_cf.loc[x, 'Area'] = area
    df_cf = df_cf[['Country', 'habitat', 'CF_occ_avg_glo', 'CF_tra_avg_glo', 'Area']].copy()
    df_cf = df_cf.rename(columns={'Country': 'Location'})

    df_cf_r = df_cf.copy()
    df_cf_r['AFDB_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['AFDB_region']).copy()
    df_cf_r['IMAGE_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['IMAGE_region']).copy()
    df_cf_r['Ecoinvent_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['Ecoinvent_region']).copy()
    df_cf_r['CF_occ_X_area'] = df_cf_r['CF_occ_avg_glo'] * df_cf_r['Area']
    df_cf_r['CF_tra_X_area'] = df_cf_r['CF_tra_avg_glo'] * df_cf_r['Area']
    for x in ['AFDB_region', 'IMAGE_region', 'Ecoinvent_region']:
        df_temp = pd.pivot_table(df_cf_r, index=[x, 'habitat'],
                                 values=['Area', 'CF_occ_X_area', 'CF_tra_X_area'], aggfunc='sum')
        df_temp.reset_index(inplace=True)
        df_temp = df_temp.rename(columns={x: 'Location'})
        df_temp = df_temp.loc[~df_temp.Location.isin(list(df_cf.Location.unique()))]
        df_temp['CF_occ_avg_glo'] = df_temp['CF_occ_X_area'] / df_temp['Area']
        df_temp['CF_tra_avg_glo'] = df_temp['CF_tra_X_area'] / df_temp['Area']
        df_cf = pd.concat([df_cf, df_temp[['Location', 'habitat', 'CF_occ_avg_glo', 'CF_tra_avg_glo', 'Area']]],
                          ignore_index=True)

    df_cf_g = pd.pivot_table(df_cf_r, index=['habitat'],
                             values=['Area', 'CF_occ_X_area', 'CF_tra_X_area'], aggfunc='sum')
    df_cf_g['CF_occ_avg_glo'] = df_cf_g['CF_occ_X_area'] / df_cf_g['Area']
    df_cf_g['CF_tra_avg_glo'] = df_cf_g['CF_tra_X_area'] / df_cf_g['Area']
    df_cf_g.reset_index(inplace=True)
    df_cf_g['Location'] = 'GLO'
    df_cf = pd.concat([df_cf, df_cf_g[['Location', 'habitat', 'CF_occ_avg_glo', 'CF_tra_avg_glo', 'Area']]],
                      ignore_index=True)
    df_cf = df_cf.dropna()
    return df_cf


def biodiversity_cf_match_locations():
    df_cf = calculate_area_weighted_regional_biodiversity_cfs()
    loc_list = get_lca_db_locations()
    for loc in loc_list:
        if loc not in list(df_cf.Location.unique()):
            if loc in lca_loc_dict.keys():
                loc2 = lca_loc_dict[loc]
            elif '-' in loc:
                loc2 = loc.split('-')[0]
                if loc2 not in loc_list:
                    print(loc2)
            else:
                loc2 = 'TBD'
                print(loc)
            df_temp = df_cf[df_cf.Location == loc2].copy()
            df_temp['Location'] = loc
            df_cf = pd.concat([df_cf, df_temp], ignore_index=True)
    df_cf.to_csv('data_regionalized_impact_assessment/interim/cf_biodiversity_processed_new.csv')
    return df_cf


def calculate_area_weighted_regional_water_cfs():
    df_cf = pd.read_excel(r'data_regionalized_impact_assessment/external/AWARE_water_CF.xlsx', engine='openpyxl', sheet_name='AWARE-annual')
    df_cf = df_cf.dropna(subset='Agg_CF_non_irri')
    df_cf.rename(columns={'Unnamed: 0': 'Country'}, inplace=True)
    df_country_aware = get_country_match_df_aware()
    df_country_globiom = get_country_match_df_globiom()
    df_country = get_country_match_df()
    df_cf['Location'] = df_cf['Country'].map(df_country_aware.set_index('AWARE')['ISO2']).copy()
    df_cf_r_2 = df_cf.loc[df_cf.Location.isna()].copy()
    df_cf_r_2['Location'] = df_cf_r_2['Country']
    df_cf_c = df_cf.loc[~df_cf.Location.isna()]
    lu_shape = gpd.read_file("data_regionalized_impact_assessment/external/shapefiles/LUID_CTY/LUID_CTY.shp")
    lu_shape = lu_shape.rename(columns={"Field2": "COUNTRY", "Field1_1": "LU_GRID"})
    lu_c = lu_shape.dissolve(by='COUNTRY')
    lu_c.reset_index(inplace=True)
    lu_c = lu_c.drop(['LU_GRID'], axis=1)
    lu_c['country_area_km2'] = lu_c['geometry'].to_crs(3395).map(lambda p: p.area / 10 ** 6)
    lu_c['Location'] = lu_c['COUNTRY'].map(df_country_globiom.set_index('GLOBIOM')['ISO2']).copy()
    df_cf_c = pd.merge(df_cf_c, lu_c, on=['Location'], how='left')
    df_cf_c = df_cf_c[['Location', 'Agg_CF_irri', 'Agg_CF_non_irri', 'country_area_km2']].copy()
    df_cf_r = df_cf_c.copy()
    df_cf_r['AFDB_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['AFDB_region']).copy()
    df_cf_r['IMAGE_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['IMAGE_region']).copy()
    df_cf_r['Ecoinvent_region'] = df_cf_r['Location'].map(df_country.set_index('ISO2')['Ecoinvent_region']).copy()
    df_cf_r['CF_irr_X_area'] = df_cf_r['Agg_CF_irri'] * df_cf_r['country_area_km2']
    df_cf_r['CF_non_irr_X_area'] = df_cf_r['Agg_CF_non_irri'] * df_cf_r['country_area_km2']
    for x in ['AFDB_region', 'IMAGE_region', 'Ecoinvent_region']:
        df_temp = pd.pivot_table(df_cf_r, index=[x],
                                 values=['country_area_km2', 'CF_irr_X_area', 'CF_non_irr_X_area'], aggfunc='sum')
        df_temp.reset_index(inplace=True)
        df_temp = df_temp.rename(columns={x: 'Location'})
        df_temp = df_temp.loc[~df_temp.Location.isin(list(df_cf_c.Location.unique()))]
        df_temp = df_temp.loc[~df_temp.Location.isin(list(df_cf_r_2.Location.unique()))]
        df_temp['Agg_CF_irri'] = df_temp['CF_irr_X_area'] / df_temp['country_area_km2']
        df_temp['Agg_CF_non_irri'] = df_temp['CF_non_irr_X_area'] / df_temp['country_area_km2']
        df_cf_c = pd.concat([df_cf_c, df_temp[['Location', 'Agg_CF_irri', 'Agg_CF_non_irri', 'country_area_km2']]],
                          ignore_index=True)
    df_cf = pd.concat([df_cf_c, df_cf_r_2[['Location', 'Agg_CF_irri', 'Agg_CF_non_irri']]],
                      ignore_index=True)
    df_cf_g = pd.DataFrame([['GLO', 45.74, 20.30]], columns=['Location', 'Agg_CF_irri', 'Agg_CF_non_irri'])
    df_cf = pd.concat([df_cf, df_cf_g], ignore_index=True)
    loc_list = get_lca_db_locations()
    for loc in loc_list:
        if loc not in list(df_cf.Location.unique()):
            if loc in lca_loc_dict.keys():
                loc2 = lca_loc_dict[loc]
            elif '-' in loc:
                loc2 = loc.split('-')[0]
                if loc2 not in loc_list:
                    print(loc2)
            else:
                loc2 = 'TBD'
                print(loc)
            df_temp = df_cf[df_cf.Location == loc2].copy()
            df_temp['Location'] = loc
            df_cf = pd.concat([df_cf, df_temp], ignore_index=True)
    df_cf.to_csv('data_regionalized_impact_assessment/interim/cf_aware_processed.csv')
    return df_cf

import bw2data as bd
import bw2io as bi
import json
import re
import functools
from bw2data import Database, config
from bw2io.strategies.generic import set_code_by_activity_hash
from bw2io.strategies import (
    assign_only_product_as_production,
    change_electricity_unit_mj_to_kwh,
    convert_activity_parameters_to_list,
    drop_unspecified_subcategories,
    fix_localized_water_flows,
    fix_zero_allocation_products,
    link_iterable_by_fields,
    link_technosphere_based_on_name_unit_location,
    migrate_datasets,
    migrate_exchanges,
    normalize_biosphere_categories,
    normalize_biosphere_names,
    normalize_simapro_biosphere_categories,
    normalize_simapro_biosphere_names,
    normalize_units,
    set_code_by_activity_hash,
    sp_allocate_products,
    split_simapro_name_geo,
    strip_biosphere_exc_locations,
    update_ecoinvent_locations,
)
from bw2io.strategies.simapro import set_lognormal_loc_value_uncertainty_safe

location_pattern = r"\{(.*?)\}"
location_pattern_2 = ", U \{.*\}"



def add_af_location(db):
    for act in db.data:
        
        act.update({"location": "unspecified"})
        if "{" in act["simapro metadata"]["Process name"]:
            match = re.findall(pattern=location_pattern, string=act["simapro metadata"]['Process name'])
            act["location"] = match[0]
            act["simapro metadata"]["Geography"] = match[0]
        
        for exc in act.get('exchanges'):
            if (
                "{" in exc.get("name")
                and ("technosphere" in exc.get("type")
                or "production" in exc.get("type"))
            ):
                match = re.findall(pattern=location_pattern, string=exc['name'])
                exc["location"] = match[0]
    return db

def change_ei_name(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if (
                "ecoinvent" in exc.get('name')
                and 'production' not in exc.get('type')
            ):
                if 'Saw dust' in exc.get('name'):
                    act_name = 'market for sawdust, wet, measured as dry mass'
                    location = 'RoW'
                else:
                    x = exc['name'].split("| ")
                    match = re.findall(pattern=location_pattern, string=exc['name'])
                    location = match[0]
                    if (
                        x[1] == "market for "
                        or x[1] == "market group for "
                       ):
                        x1 = x[0].split(" {")
                        act_name = f"{x[1]}{x1[0].lower()}"
                    else:
                        act_name = x[1].rstrip()
                exc['name'] = act_name
                exc['location'] = location
    return db

def change_remaining_techno_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'technosphere':
                if (
                        'market for sodium hydroxide, without water, in 50% solution state' == exc.get('name')
                        and exc.get("location") == "GLO"
                ):
                    exc['location'] = "RoW"
                if (
                        'market for benzene' == exc.get('name')
                        and exc.get("location") == "GLO"
                ):
                    exc['location'] = "RoW"
                if (
                        'market for sodium bicarbonate' == exc.get('name')
                        and exc.get("location") == "GLO"
                ):
                    exc['location'] = "RoW"
                if (
                        'Hazardous waste, landfill' == exc.get('name')
                ):
                    exc["name"] = 'Hazardous waste disposed'
                    exc["type"] = "biosphere"
                    exc["categories"] = ('inventory indicator', 'waste')
                if exc["name"] in ["Overburden (deposited)",
                                   "Spoil, unspecified",
                                   "Tailings, unspecified",
                                   "Waste, nuclear, low and medium active/m3",
                                   "Slags",
                                   "Radioactive waste",
                                   "Waste, nuclear, high active/m3",
                                   "Waste in inert landfill",
                                   "Packaging waste, plastic",
                                   "Waste, toxic",
                                   "Zinc slag, unspecified",
                                   "Packaging waste, metal",
                                   "Chemical waste, inert",
                                   "Demolition waste, unspecified",
                                   "Waste, organic",
                                   "Mineral waste",
                                   "Zinc waste",
                                   "Municipal waste, unspecified",
                                   "Carcass meal",
                                   "Oil waste",
                                   "Jarosite",
                                   "Refractory",
                                   "Waste, industrial",
                                   "Bauxite residue, from aluminium production",
                                   "Radioactive tailings"]:
                    exc["type"] = "biosphere"

    return db

def unit_exchange_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if (
                "heat production" in exc.get('name')
                and "kilowatt hour" == exc.get('unit')
            ):
                exc['unit'] = "megajoule"
                exc['amount'] *= 3.6
                exc['loc'] *= 3.6
            elif (
                "electricity, low voltage" in exc.get('name')
                and "megajoule" == exc.get('unit')
            ):
                exc['unit'] = "kilowatt hour"
                exc['amount'] /= 3.6
                exc['loc'] /= 3.6
            elif (
                'market for wastewater' in exc.get('name')
                and 'litre' == exc.get('unit')
            ):
                exc['unit'] = "cubic meter"
                exc['amount'] *= 0.001
                exc['loc'] *= 0.001
    return db

# Change names to contain "in ground"
def change_in_ground_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if (
                    exc.get('type') == 'biosphere'
                    and "natural resource" in exc.get('categories')
                    and "in ground" in exc.get('name')
            ):
                x = exc["name"].split(", in ground")
                exc['name'] = x[0]
                exc['categories'] = ('natural resource', 'in ground')
    return db


# add "in ground" to "categories"
def change_in_ground_categories_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if (
                    exc.get('type') == 'biosphere'
                    and "in ground" in exc.get('name')
                    and ('natural resource',) == exc.get('categories')
            ):
                x = exc["name"].split(", in ground")
                exc['name'] = x[0]
                exc['categories'] = ('natural resource', 'in ground')
    return db


# change names of unlinked containing "water"
def change_water_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere' and "Water, " in exc.get('name'):
                x = exc['name'].split(", ")
                exc_name = f"{x[0]}, {x[1]}"
                if "Water, cooling" in exc_name:
                    exc['name'] = 'Water, cooling, unspecified natural origin'
                    exc['categories'] = ('natural resource', 'in water')
                    if exc['unit'] == "kilogram":
                        exc['amount'] /= 1000
                        exc['unit'] = 'cubic meter'
                elif "Water, turbine use" in exc_name:
                    exc['name'] = 'Water, turbine use, unspecified natural origin'
                    exc['categories'] = ('natural resource', 'in water')
                elif "Water, river" in exc_name or "Water, lake" in exc_name:
                    exc['name'] = exc_name
                    exc['categories'] = ('natural resource', 'in water')
                elif "Water, well" in exc_name:
                    exc['name'] = 'Water, well, in ground'
                    exc['categories'] = ('natural resource', 'in water')
                elif "Water, salt" in exc_name:
                    exc['name'] = 'Water, salt, ocean'
                    exc['categories'] = ('natural resource', 'in water')
                #elif "Water, rain" in exc_name:
                #    exc["name"] = "Water, unspecified natural origin"
                #    exc["categories"] = ('natural resource', 'in water')
                elif "Water" in exc_name and ("air","stratosphere") == exc.get("categories"):
                    exc["name"] = "Water, in air"
                    exc["categories"] = ("natural resource", "in air")
                elif exc_name in ['Water, BR-Mid-western grid',
                                  'Water, BR-South-eastern grid',
                                  'Water, Europe without Austria',
                                  'Water, Europe without Switzerland and Austria',
                                  'Water, RER w/o RU',
                                  'Water, unspecified natural origin',
                                  'Water, fresh']:
                    exc['name'] = 'Water, unspecified natural origin'
                    exc['categories'] = ('natural resource', 'in water')
                    if exc['unit'] == "litre":
                        exc['amount'] /= 1000
                        exc['unit'] = 'cubic meter'
    return db


# change names of unlinked containing "nitrogen"
def change_nitrogen_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if (
                        "Nitrogen, atmospheric" in exc.get('name')
                        or "Nitrogen, total" in exc.get('name')
                ):
                    exc['name'] = "Nitrogen"
                elif (
                        "Nitrogen dioxide" in exc.get('name')
                        and exc.get('categories') == ('water', 'ground-')
                ):
                    exc['name'] = "Nitrogen dioxide"
                    exc['categories'] = ('water', 'surface water')
                elif (
                        "Nitrogen monoxide" in exc.get('name')
                        or "Nitrogen oxides" in exc.get('name')
                        or "Nitrogen dioxide" in exc.get('name')
                ):
                    exc['name'] = "Nitrogen oxides"
                elif (
                        "Nitrogen, NO" in exc.get('name')
                        or "Nitrogenous Matter (unspecified, as N)" in exc.get('name')
                ):
                    exc['name'] = "Nitrogen"
    return db


# Change names to contain "NMVOC"
def change_nmvoc_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if (
                    exc.get('type') == 'biosphere'
                    and ("NMVOC" in exc_name or "VOC" in exc_name)
                    and ", unspecified origin" in exc_name
            ):
                exc['name'] = exc["name"].removesuffix(", unspecified origin")
    return db


# remove locations new
def change_remove_location_bio(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if (
                    exc.get('type') == 'biosphere'
                    and re.findall("(, [A-Z][A-Z])",exc_name)
            ):
                split_point = re.findall("(, [A-Z][A-Z])",exc_name)
                new_name = exc_name.split(split_point[0])[0]
                exc['name'] = new_name
    return db

# remove locations      NOT USED
def change_remove_location_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if (
                    exc.get('type') == 'biosphere'
                    and ',' in exc_name
                    and ('Ammonia' in exc_name
                         or 'Nitrate' in exc_name
                         or 'Phosphorus' in exc_name
                         or 'Sulfur dioxide' in exc_name)
            ):
                x = exc_name.split(", ")
                exc['name'] = x[0]
    return db


# rename PMs
def change_pm_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if (
                    exc.get('type') == 'biosphere'
                    and "Particulates" in exc_name
            ):
                exc['name'] = exc["name"].removeprefix("Particulates")
                exc["name"] = "Particulate Matter" + exc["name"]
    return db


# remove peat oxidation
def change_remove_peat_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if (
                    exc.get('type') == 'biosphere'
                    and ', peat oxidation' in exc.get('name')
            ):
                if "Methane" in exc.get('name') or "Carbon dioxide" in exc.get("name"):
                    x = exc_name.split(", ")
                    exc["name"] = x[0] + ", fossil"
                else: 
                    x = exc_name.split(", ")
                    exc['name'] = x[0]
    return db


# LUC
def change_luc_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (
                        'land' not in exc.get('categories')
                        and ('Transformation,' in exc.get('name')
                             or 'Occupation,' in exc.get('name'))
                ):
                    exc['categories'] = ('natural resource', 'land')
                if (
                        'Transformation, to annual crop' in exc_name
                        or 'Transformation, to permanent crop' in exc_name
                        or  'Transformation, from annual crop' in exc_name
                        or 'Transformation, from permanent crop' in exc_name
                        or 'Occupation, permanent crop' in exc_name
                        or 'Occupation, annual crop' in exc_name
                ):
                    x = exc_name.split(", ")
                    exc['name'] = f"{x[0]}, {x[1]}"
                elif 'Transformation, from forest, extensive' in exc_name:
                    x = exc_name.split(", ")
                    exc['name'] = f"{x[0]}, {x[1]}, {x[2]}"
                elif 'Transformation, to grassland/pasture/meadow' in exc_name:
                    exc["name"] = "Transformation, to grassland, natural, for livestock grazing"
                elif 'Transformation, from grassland/pasture/meadow' in exc["name"]:
                    exc["name"] = "Transformation, from grassland, natural, for livestock grazing"
                elif 'Occupation, grassland/pasture/meadow' in exc["name"]:
                    exc["name"] ="Occupation, grassland, natural, for livestock grazing"
                    
    return db


# energy
def change_energy_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (
                        'Energy, potential (in hydropower reservoir), converted' == exc_name
                        or 'Energy, from hydro power' == exc_name
                ):
                    exc['categories'] = ('natural resource', 'in water')
                    exc['name'] = 'Energy, potential (in hydropower reservoir), converted'
                elif 'Energy, from biomass' == exc_name:
                    exc['categories'] = ('natural resource', 'biotic')
                    exc['name'] = 'Energy, gross calorific value, in biomass'
                elif 'Energy, from wood' == exc_name:
                    exc['categories'] = ('natural resource', 'biotic')
                    exc['name'] = 'Energy, gross calorific value, in biomass, primary forest'
    return db


# add elements to categories
def change_add_elements_categories_acts(db, soil_check_list, water_check_list, air_check_list):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if (
                        ('soil',) == exc.get('categories')
                        and exc.get('name') in soil_check_list
                ):
                    exc['categories'] = ('soil', 'agricultural')
                elif (
                        ('water',) == exc.get('categories')
                        and exc.get('name') in water_check_list
                ):
                    exc['categories'] = ('water', 'surface water')
                elif (
                        ('air',) == exc.get('categories')
                        and exc.get('name') in air_check_list
                ):
                    exc['categories'] = ('air', 'non-urban air or from high stacks')
    return db

def change_remove_elements_categories(db, chemicals_checklist_remove_specific_category):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if (
                        exc.get("name") in chemicals_checklist_remove_specific_category
                ):
                    
                    exc["categories"] = exc["categories"][0]

    return db


def change_to_soil_agricultural_categories(db, chemicals_checklist_soil_agricultural):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if (
                        exc.get("name") in chemicals_checklist_soil_agricultural
                ):
                    exc["categories"] = ('soil', 'agricultural')

    return db

def change_categories_bio_acts(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if (
                        'Magnesium, 0.13% in water' == exc.get('name')
                        and ('natural resource', 'in ground') == exc.get('categories')
                ):
                    exc['categories'] = ('natural resource', 'in water')
                elif (
                        'Wood, soft, standing' == exc.get('name')
                        and ('natural resource', 'in ground') == exc.get('categories')
                ):
                    exc['categories'] = ('natural resource', 'biotic')
                elif (
                        'Fish' in exc.get('name')
                        and ('natural resource', 'in water') == exc.get('categories')
                ):
                    exc['categories'] = ('natural resource', 'biotic')
                elif (
                        'Methane' == exc.get('name')
                        and ('air',) == exc.get('categories')
                ):
                    exc['categories'] = ('air', 'urban air close to ground')
                elif (
                        'Phosphorus' == exc.get('name')
                        and ('natural resource',) == exc.get('categories')
                ):
                    exc['categories'] = ('natural resource', 'in ground')
                    exc['name'] = 'Phosphorus, in ground'
                elif (
                        'Pyraclostrobin (prop)' == exc.get('name')
                        and 'water' in exc.get('categories')
                ):
                    exc['name'] = 'Pyraclostrobin'
                elif (
                        'Sylvite, 25 % in sylvinite, in ground' == exc.get('name')
                        and ('natural resource',) == exc.get('categories')
                ):
                    exc['categories'] = ('natural resource', 'in ground')
                elif (
                        'Hydrochloric acid' == exc.get('name')
                        and 'water' in exc.get('categories')
                ):
                    exc['categories'] = ('water',)
                elif (
                        exc.get('name') in ['Nitrate', 'Chlorine', 'PAH, polycyclic aromatic hydrocarbons',
                                            'Sulfate']
                        and 'soil' in exc.get('categories')
                ):
                    exc['categories'] = ('soil',)
                elif (
                        exc.get('name') in ['Azoxystrobin', 'Metribuzin', 'Diquat dibromide',
                                            'Chlorpyrifos', 'Imidacloprid']
                        and 'water' in exc.get('categories')
                ):
                    exc['categories'] = ('water', 'ground-')
                elif (
                        "Oxygen" in exc.get('name')
                         and "natural resource" in exc.get("categories")
                ):
                    exc["categories"] = ("natural resource", "in air")
                elif (
                        "industrial" in exc.get("categories")
                ):
                    exc["categories"] = ("soil",)
                elif (
                        "Peat" in exc.get("name")
                        and ('natural resource', 'in ground') == exc.get("categories")
                ):
                    exc["categories"] = ('natural resource', 'biotic')
                elif (
                        "Energy, gross calorific value, in biomass" in exc.get("name")
                        and ('natural resource',) == exc.get("categories")
                ):
                    exc["categories"] = ('natural resource', 'biotic')
                elif (
                        "Osmium" in exc.get("name")
                        and ('natural resource',) == exc.get("categories")
                ):
                    exc["categories"] = ('natural resource', 'in ground')
                
                '''
                elif (
                        "Ammonia" in exc.get("name")
                        and ('water',) in exc.get("categories")
                ):
                    exc["name"] = "Ammonium"
                elif (
                        "Ammonium" in exc.get("name")
                        and ('air',) in exc.get("categories")
                ):
                    exc["name"] = "Ammonia"
                elif (
                        "Fluorine" in exc.get("name")
                        and ('water', "ground-") in exc.get("categories")
                ):
                    exc["categories"] = ('water', 'surface water')
                elif (
                        "Fluoranthene" in exc.get("name")
                        and ('water', "ground-") in exc.get("categories")
                ):
                    exc["categories"] = ('water', 'surface water')
                elif (
                        "Benz(a)anthracene" in exc.get("name")
                        and ('water', "ground-") in exc.get("categories")
                ):
                    exc["categories"] = ('water', 'surface water')
                elif (
                        "Deltamethrin" in exc.get("name")
                        and ('water', "surface water") in exc.get("categories")
                ):
                    exc["categories"] = ('water', 'ground-')
                elif (
                        "Chrysene" in exc.get("name")
                        and ('water', "ground-") in exc.get("categories")
                ):
                    exc["categories"] = ('water', 'surface water')
                '''

    return db



def change_stratosphere(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if exc.get("categories") == ('air', 'stratosphere'):
                    exc["categories"] = ('air', 'lower stratosphere + upper troposphere')
    return db

def change_percentages(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if "%" in exc_name:
                    x = exc_name.split(", ")
                    exc["name"] = x[0]
    return db

def change_radioactive_unit(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            if exc.get('type') == 'biosphere':
                if act.get("name") in ["Tellurium-123",
                                        "Lead-210",
                                        "Radium-228",
                                        "Manganese-55",
                                        "Radium-226",
                                        "Americium-241",
                                        "Zirconium-95",
                                        "Uranium-234",
                                        "Plutonium-alpha",
                                        "Iodine-129",
                                        "Strontium-90",
                                        "Thorium-230",
                                        "Uranium-235",
                                        "Uranium-238",
                                        "Technetium-99",
                                        "Radium-228"
                                        "Radioactive species, Nuclides, unspecified"]:
                    exc["unit"] = "kilo Becquerel"
    return db

def change_methane_flows(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (exc_name == "Methane"
                    and "air" in exc.get("categories")
                ):
                    exc["name"] = "Methane, non-fossil"
                elif ("Methane" in exc_name
                      and "," in exc_name
                      and "fossil" not in exc_name
                ):
                    x = exc_name.split(", ")
                    x1 = x[1].capitalize()
                    x1 = x1.removesuffix("-")
                    x0 = x[0].lower()
                    exc["name"] = x1 + x0

    return db

def change_chemical_flows(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (("Ethane" in exc_name
                    or "Benzene" in exc_name
                    or "Chlorosilane" in exc_name
                    or "Phenol" in exc_name
                    or "Ethene" in exc_name
                    or "Toluene" in exc_name
                    or "Cyclopentane" in exc_name
                    or "Chlorosilane" in exc_name
                    or "Propane" in exc_name
                    or "Chrysene" in exc_name
                    or "Phthalate" in exc_name
                    or "Naphthalene" in exc_name
                    or "Butane" in exc_name
                    or "Fluorene" in exc_name)
                    and ", " in exc_name
                ):
                    x = exc_name.split(", ")
                    x1 = x[1].capitalize()
                    x1 = x1.removesuffix("-")
                    x0 = x[0].lower()
                    exc["name"] = x1 + x0

    return db

def change_potassium(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if ((exc_name == "Potassium"
                      or exc_name == "Potassium, ion")
                      and "natural resource" in exc.get("categories")
                ):
                    exc["categories"] = ('natural resource', 'in ground')
                elif ((exc_name == "Potassium"
                      or exc_name == "Potassium, ion")
                      and "natural resource" not in exc.get("categories")
                ):
                    exc["name"] = "Potassium I"

    return db

def change_cadmium_chromium_lithium_zinc(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (exc_name == "Cadmium, ion"
                      and "water" in exc.get("categories")
                ):
                    exc["name"] = ("Cadmium II")
                if (exc_name == "Chromium, ion"
                      and "water" in exc.get("categories")
                ):
                    exc["name"] = ("Chromium III")
                if (exc_name == "Lithium, ion"
                      and "water" in exc.get("categories")
                ):
                    exc["name"] = ("Lithium I")
                if (exc_name == "Zinc, ion"
                      and "water" in exc.get("categories")
                ):
                    exc["name"] = ("Zinc II")
    return db

def change_rest(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if (exc_name == "Dichlorobenzene"
                      and exc.get("categories") == ("air","non-urban air or from high stacks")
                ):
                    exc["name"] = ("1,3-dichlorobenzene")
                if (exc_name == "1,2-dichloroethane"
                      and exc.get("categories") == ("air","non-urban air or from high stacks")
                ):
                    exc["name"] = ("Dichloroethane")
                    exc["categories"] = ("air",)
                if (exc_name == "Sylvite"
                      and "natural resource" in exc.get("categories")
                ):
                    exc["categories"] = ("natural resource","in ground")
                if (exc_name == "Benzo(a)anthracene"
                      and "air" in exc.get("categories")
                ):
                    exc["categories"] = ("are","lower stratosphere + upper stratosphere")
                if (exc_name == "Fish, pelagic, in ocean"
                      and "natural resource" in exc.get("categories")
                ):
                    exc["categories"] = ("natural resource","biotic")
                if (exc_name == "o-dichlorobenzene"
                      and exc.get("categories") == ("soil","agricultural")
                ):
                    exc["name"] = "o-Dichlorobenzene"
    return db

def change_minerals(db):
    for act in db.data:
        for exc in act.get('exchanges'):
            exc_name = exc.get('name')
            if exc.get('type') == 'biosphere':
                if ((exc_name == "Aluminium"
                    or exc_name == "Antimony"
                    or exc_name == "Arsenic V"
                    or exc_name == "Barium"
                    or exc_name == "Beryllium"
                    or exc_name == "Cadmium"
                    or exc_name == "Calcium"
                    or exc_name == "Chromium"
                    or exc_name == "Cobalt"
                    or exc_name == "Copper"
                    or exc_name == "Iron"
                    or exc_name == "Lead"
                    or exc_name == "lithium"
                    or exc_name == "Manganese"
                    or exc_name == "Mercury"
                    or exc_name == "Molybdenum"
                    or exc_name == "Nickel"
                    or exc_name == "Nickel, ion"
                    or exc_name == "Rhodium"
                    or exc_name == "Selenium"
                    or exc_name == "Silver"
                    or exc_name == "Sodium"
                    or exc_name == "Strontium"
                    or exc_name == "Thallium"
                    or exc_name == "Tin"
                    or exc_name == "Titanium"
                    or exc_name == "Vanadium"
                    or exc_name == "Zinc"
                    or exc_name == "Palladium"
                    or exc_name == "Chromium IV"
                    or exc_name == "Calcium, ion"
                    or exc_name == "Sodium, ion"
                    or exc_name == "Aluminium, ion"
                    or exc_name == "Ammonium, ion"
                    or exc_name == "Silver, ion"
                    or exc_name == "Cesium"
                    or exc_name == "Vanadium, ion"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium")
                    and "natural resource" in exc.get("categories")
                ):
                    exc["categories"] = ('natural resource', 'in ground')
                elif ((exc_name == "Aluminium"
                    or exc_name == "Antimony"
                    or exc_name == "Arsenic V"
                    or exc_name == "Barium"
                    or exc_name == "Beryllium"
                    or exc_name == "Cadmium"
                    or exc_name == "Calcium"
                    or exc_name == "Chromium"
                    or exc_name == "Cobalt"
                    or exc_name == "Copper"
                    or exc_name == "Iron"
                    or exc_name == "Lead"
                    or exc_name == "lithium"
                    or exc_name == "Manganese"
                    or exc_name == "Mercury"
                    or exc_name == "Molybdenum"
                    or exc_name == "Nickel"
                    or exc_name == "Nickel, ion"
                    or exc_name == "Rhodium"
                    or exc_name == "Selenium"
                    or exc_name == "Silver"
                    or exc_name == "Sodium"
                    or exc_name == "Strontium"
                    or exc_name == "Thallium"
                    or exc_name == "Tin"
                    or exc_name == "Titanium"
                    or exc_name == "Vanadium"
                    or exc_name == "Zinc"
                    or exc_name == "Palladium"
                    or exc_name == "Chromium IV"
                    or exc_name == "Calcium, ion"
                    or exc_name == "Sodium, ion"
                    or exc_name == "Aluminium, ion"
                    or exc_name == "Ammonium, ion"
                    or exc_name == "Silver, ion"
                    or exc_name == "Cesium"
                    or exc_name == "Vanadium, ion"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium"
                    or exc_name == "Palladium")
                    and "natural resource" not in exc.get("categories")
                ):
                    exc["name"] = exc_name + " - new"

    return db

def write_unlinked_biosphere(db):
    ag_bio_name = "biosphere agrifootprint unlinked"
    try:
        del bd.databases[ag_bio_name]
    except:
        pass
    bd.Database(ag_bio_name).register()
    db.add_unlinked_flows_to_biosphere_database(ag_bio_name)

def import_agrifootprint(ei_name,bio_name):
    af_path = "C:/Users/arminsi/polybox - Armin Siegrist/ETH working folder/Modular LCA/Databases/agrifootprint_6_3_all_allocations.csv"
    af_name = "agrifootprint 6.3 all allocations"
    bio3 = bd.Database("ecoinvent-3.10-biosphere")
    if af_name in bd.databases:
            print(f'{af_name} is already imported.')
    else:
        print(f'start importing {af_name}.')
        af = bi.SimaProCSVImporter(
            filepath=af_path,
            name=af_name,
            delimiter=";"
        )
        
        
        migration_name = "agrifootprint-6-names"
        bi.Migration(migration_name).write(
            json.load(open("C:/Users/arminsi/polybox - Armin Siegrist/ETH working folder/Modular LCA/Python_script/bw_set_up/Agrifootprint_6_economic_new.json")),
            "Change names of agrifootprint activities",
        )

        soil_agri_list = [act['name'] for act in bio3 if "agricultural" in act['categories']]
        soil_list = [act['name'] for act in bio3 if ('soil',) == act['categories']]
        soil_check_list = [x for x in soil_agri_list if x not in soil_list]
        water_surface_list = [act['name'] for act in bio3 if "surface water" in act['categories']]
        water_list = [act['name'] for act in bio3 if ('water',) == act['categories']]
        water_check_list = [x for x in water_surface_list if x not in water_list]
        air_high_list = [act['name'] for act in bio3 if "non-urban air or from high stacks" in act['categories']]
        air_list = [act['name'] for act in bio3 if ('air',) == act['categories']]
        air_check_list = [x for x in air_high_list if x not in air_list]
        
        af = change_ei_name(af)
        af = change_remaining_techno_acts(af)

        strategies = [
            normalize_units,
            update_ecoinvent_locations,
            assign_only_product_as_production,
            drop_unspecified_subcategories,
            sp_allocate_products,
            fix_zero_allocation_products,
            split_simapro_name_geo,
            strip_biosphere_exc_locations,
            functools.partial(migrate_datasets, migration="default-units"),
            functools.partial(migrate_exchanges, migration="default-units"),
            functools.partial(set_code_by_activity_hash, overwrite=True),
            link_technosphere_based_on_name_unit_location,
            change_electricity_unit_mj_to_kwh,
            set_lognormal_loc_value_uncertainty_safe,
            normalize_biosphere_categories,
            normalize_simapro_biosphere_categories,
            normalize_biosphere_names,
            normalize_simapro_biosphere_names,
            functools.partial(migrate_exchanges, migration="simapro-water"),
            fix_localized_water_flows,
            functools.partial(
                    link_iterable_by_fields,
                    other=Database(bio3 or config.biosphere),
                    kind="biosphere",
                ),
            convert_activity_parameters_to_list
        ]

        af.apply_strategies(strategies=strategies)

        af = add_af_location(af)
        af = unit_exchange_acts(af)
        af.match_database(ei_name, fields=("name", "unit", "location"))
        af.match_database(bio_name, fields=("name", "unit", "categories"))
        af = change_percentages(af)
        af = change_chemical_flows(af)
        af = change_minerals(af)
        af.migrate(migration_name)
        af = change_in_ground_categories_acts(af)
        af = change_in_ground_acts(af)
        af = change_water_acts(af)
        af = change_nitrogen_acts(af)
        af = change_nmvoc_acts(af)
        af = change_remove_location_bio(af)
        af = change_pm_acts(af)
        af = change_remove_peat_acts(af)
        af = change_luc_acts(af)
        af = change_energy_acts(af)
        af = change_add_elements_categories_acts(af, soil_check_list, water_check_list, air_check_list)
        af = change_categories_bio_acts(af)
        af = change_stratosphere(af)
        af = change_radioactive_unit(af)
        af = change_methane_flows(af)
        af = change_potassium(af)
        af = change_cadmium_chromium_lithium_zinc(af)
        af = change_rest(af)

        af.match_database(bio_name, fields=("name", "unit", "categories"))
        af.statistics()


        write_unlinked_biosphere(af)
        af.match_database("biosphere agrifootprint unlinked", fields=("name", "unit", "categories"))
        af.drop_unlinked(i_am_reckless=True)
        af.write_database()
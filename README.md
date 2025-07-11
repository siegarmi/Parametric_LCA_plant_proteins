# Parametric LCA (Life Cycle Assessment) model for plant protein processing

This repository contains the model code and required input data files for parametric LCAs of plant protein value chains based on variable process parameters and geographical locations.

This repository is currently only public for review purposes. Once the corresponding publication is published, the code and related documents will be made available for public use with an MIT license.

## The model

Currently, the model is designed to calculate environmental impacts for the value chains of pea protein isolate (PPI) and concentrate (PPC), soy protein isolate (SPI) and concentrate (SPC), and wheat gluten (WG).

### System boundaries

They system boundaries can be chosen flexibly based on the following processes:
- Cultivation
- Pre-treatment
- Milling
- Defatting
- Protein extraction (Various technologies)
- Transport between processes and until point-of-use.

### Geographical scope

The geographical scope includes all European countries for the processing steps. Countries for cultivation are principally limited by the coverage of the Agrifootprint database. However, there is a function implemented that creates cultivation processes based on the closest available country in the Agrifootprint database by adapting, e.g., electricity mixes but not local conditions such as the availability of peat soils. Additionally, the US is available for the cultivation and processing of soy, Brazil for the cultivation of soy, and China for the cultivation and processing of pea, soy, and wheat. For processing in the US or China, no transport between the cultivation and processing facility can be modelled currently (assumption that it is nearby or on the way to the port).

### Functional units

Currently, a mass- and protein-based functional unit can be selected. Variable protien contents of the final product can be accounted for when using a protein-based functional unit.

### Multi-functionality

Currently, multi-functionality of processes is dealt with by economic allocation (but any allocation type possible). The uncertainty of allocation factors can be taken into account in the models.

### Impact assessment

Currently, the model calculates environmental impacts based on regional characterization factors for water stress, land use related biodiversity loss, and particulate matter related human health impacts. For climate change, the factors from IPCC are used. However, any other impact assessment can be added to the model

## Model dependencies

The model is based on the [Brightway 2](https://github.com/brightway-lca/brightway2) library and [lca_algebraic](https://github.com/oie-mines-paristech/lca_algebraic/).

The model relies on [ecoinvent](https://ecoinvent.org/) as a background database. Therefore, an ecoinvent license is required to use the model. For agricultural processes, the model currently relies on processes from the [Agrifootprint](https://blonksustainability.nl/agri-footprint) v6.3 database. However, the model can be modified to use agricultural processes from other databases or self-created inventories (see possible adjustments below).

## How to use the model?

1. Pull the entire folder from GitHub

2. Install the necessary python environments from the provided yaml files. For this you can run the following line in your terminal for each environment:

`conda env create -f your_folder_path/Parametric_LCA_plant_proteins/environment_name.yaml`

3. Change the path to your folder location in the beginning of the files "Parametrized_LCA_script.py" and "Figures_parametrized_LCA.ipynb" in the folder Code.

4. Specify the value chains you want to model in "Data input" --> "Input files value chains" --> "Value_chains.xlsx". Save the file as "Value_chains.csv" in "Data input" --> "Input_files_csv" --> "Parameterized_model

5. If used, save the Agrifootprint database as "agrifootprint_6_3_all_allocations.csv" in the folder "Databases. Other versions of the database should work too, but might need adjustments in the file "import_agrifootprint_db_functions.py"

6. Run the python script "Parametrized_LCA_script.py" in the folder "Code". The results will be stored in the "Parametrized_LCA_results" folder. A file indicating the changes that have been made will be stored in the folder "Track_change".

7. If you wish, you can use the functions of "Figures_parametrized_LCA.ipynb" to visualize your results. They might need to be adjusted if the number of value chains changes significantly for optimal visualization.

## Possible adjustments of the model for further applications

1. Use different cultivation activities instead of the ones provided in the Agrifootprint database to cover more countries, increase the resolution to a sub-country level, or investigate different cultivation practices deviating from the average cultivation.

This would require changing lines 141-142 and 190-196 in "Parametrized_LCA_script.py" as well as the depending functions.

2. Expand the transport to other countries apart from Europe and the production locations in Brazil, China, and the US to model value chains outside of the European context or add more supplying countries.

This would require to update the .csv files in the folder "Data input" --> Input_files_csv" --> "transport" based on the approach described in the manuscript (...) (or any other approach). Further, the tab "Countries" in the file "Value_chains.xlsx" in "Data input" --> "Input files value chains" would need to be updated to include the updated list of possible countries.

3. Conduct LCAs for different products or update the process parameters for the available processes.

This would require different model parameters tailored to the products of interest. They can be set up as shown for pea, soy, and wheat proteins in the excel file "Processing_data.xlsx" in the folder "Data input" --> "Input files value chains". There also process parameters can be updated. Afterwards the model parameters and the Formulas must be saved as .csv files in the folder "Data input" --> "Input_files_csv" --> "Parameterized_model"

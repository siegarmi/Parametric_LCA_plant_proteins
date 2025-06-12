import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def store_file_as_df_in_dict(dict,file_name,folder_path,name_part,index_col_num=None):
    file_path = os.path.join(folder_path, file_name)
    df = pd.read_csv(file_path,index_col=index_col_num)
    
    # Store the DataFrame in the dictionary with the filename (without extension) as the key
    key = "-".join([os.path.splitext(file_name)[0].split("_")[i][:-3] for i in name_part])
    dict[key] = df
    return dict

def align_dataframes(df_dict):
    # Step 1: Get the union of all row indices across all DataFrames
    all_indices = set()
    for df in df_dict.values():
        all_indices.update(df.index)
    all_indices = sorted(all_indices)

    # Step 2: Reindex each DataFrame, filling missing rows with 0
    aligned_dict = {}
    for key, df in df_dict.items():
        aligned_df = df.reindex(all_indices).fillna(0)
        aligned_dict[key] = aligned_df

    return aligned_dict

def sum_transport_rows(df_dict):
    result_dict = {}

    for key, df in df_dict.items():
        # Identify transport-related rows
        transport_mask = df.index.str.contains("transport", case=False)

        # Sum those rows into one row
        transport_sum = df[transport_mask].sum(axis=0)

        # Drop transport-related rows
        df_cleaned = df[~transport_mask]

        # Add the new "Transport distances" summary row
        transport_row = pd.DataFrame([transport_sum], index=["Transport distances"])

        # Append and return
        df_result = pd.concat([df_cleaned, transport_row])
        result_dict[key] = df_result

    return result_dict

def format_impact_data(df,GWP_impacts,PM25_impacts,WU_impacts,LU_impacts):
    GWP_impacts.append(list(df["GWP_100a - all[CO2-eq]"]))
    PM25_impacts.append(list(df["Particulate matter - health impacts (PMHI)[DALY]"]))
    WU_impacts.append(list(df["Water stress - Annual[m3 world]"]))
    Sum_LU_impacts = [x + y for x, y in zip(list(df["Occupation - Biodiversity loss (LUBL)[PDF*year/m2a]"]),list(df["Transformation - Biodiversity loss (LUBL)[PDF*year/m2]"]))]
    LU_impacts.append(Sum_LU_impacts)
    return GWP_impacts, PM25_impacts, WU_impacts, LU_impacts

def calculate_mean_contributions(df,product,countries):
    mean_values = df.mean()

    index_label = f"{product}_{countries}"
    summary_df = pd.DataFrame([mean_values], index=[index_label])

    return summary_df

def clean_and_sort_dataframe(df):
    #Define processes and impacts in the desired order
    processes = [
        'crop', 'dehulling', 'milling', 'defatting', 'protein_separation',
        'Heat_protein_separation', 'Electricity_protein_separation', 'Transport'
    ]

    impact_order = [
        "GWP_100a - all[CO2-eq]",
        "Particulate matter - health impacts (PMHI)[DALY]",
        "Water stress - Annual[m3 world]",
        "Total - Biodiversity loss (LUBL)[PDF]"
    ]

    #Drop unwanted impact types
    drop_impacts = [
        "GWP_100a - Biogenic[CO2-eq]",
        "GWP_100a - Fossil[CO2-eq]",
        "GWP_100a - LUC[CO2-eq]"
    ]
    df = df.drop(columns=[col for col in df.columns if any(imp in col for imp in drop_impacts)], errors='ignore')

    #Calculate total biodiversity loss per process
    for process in processes:
        occ_col = f"{process} - Occupation - Biodiversity loss (LUBL)[PDF*year/m2a]"
        trans_col = f"{process} - Transformation - Biodiversity loss (LUBL)[PDF*year/m2]"
        total_col = f"{process} - Total - Biodiversity loss (LUBL)[PDF]"

        if occ_col in df.columns and trans_col in df.columns:
            df[total_col] = df[occ_col] + df[trans_col]
            df = df.drop(columns=[occ_col, trans_col])

    #Add missing columns filled with 0
    for process in processes:
        for impact in impact_order:
            col_name = f"{process} - {impact}"
            if col_name not in df.columns:
                df[col_name] = 0.0

    #Sort columns by process and impact
    sorted_columns = []
    for impact in impact_order:
        for proc in processes:
            sorted_columns.append(f"{proc} - {impact}")

    df = df[sorted_columns]

    impact_rename_map = {
        "GWP_100a - all[CO2-eq]": "GWP",
        "Particulate matter - health impacts (PMHI)[DALY]": "PMHI",
        "Water stress - Annual[m3 world]": "WS",
        "Total - Biodiversity loss (LUBL)[PDF]": "LUBL"
    }

    new_columns = []
    for col in df.columns:
        process, impact = col.split(" - ", 1)
        short_impact = impact_rename_map.get(impact, impact)
        new_columns.append(f"{process} - {short_impact}")

    df.columns = new_columns

    return df

def add_break_marks(ax, where='top', size=0.015, lw=1.5):
    if where == 'top':
        # Top-left
        ax.plot([0-0.5*size, 0.5*size], [1-0.5*size, 1 + 0.5*size],
                transform=ax.transAxes, color='k', lw=lw, clip_on=False)
        # Top-right
        ax.plot([1 - 0.5*size, 1+0.5*size], [1-0.5*size, 1 + 0.5*size],
                transform=ax.transAxes, color='k', lw=lw, clip_on=False)

    elif where == 'bottom':
        # Bottom-left
        ax.plot([0-0.5*size, 0.5*size], [0-0.5*size, 0.5*size],
                transform=ax.transAxes, color='k', lw=lw, clip_on=False)
        # Bottom-right
        ax.plot([1 - 0.5*size, 1+0.5*size], [0-0.5*size, 0.5*size],
                transform=ax.transAxes, color='k', lw=lw, clip_on=False)

def plot_violin(ax, data, data_protein, ylabel, xtick_label, label, edge_colors, face_colors,y_lower_lim=None,position_label=[-0.1,1.1]):
    vp = ax.violinplot(data, showmedians=True)
    vp2 = ax.violinplot(data_protein, showmedians=True)
    ax.set_xticks(range(1,len(xtick_label)+1))
    ax.set_xticklabels(xtick_label,multialignment="center")  
    ax.set_xlabel('Products')
    ax.set_ylabel(ylabel)

    current_ylim = ax.get_ylim()
    if y_lower_lim:
        ax.set_ylim(bottom=current_ylim[0]*1.05,top=current_ylim[1]*1.05)
    else:
        ax.set_ylim(bottom=y_lower_lim,top=current_ylim[1]*1.05)

    ax.text(position_label[0], position_label[1], label, transform=ax.transAxes,
            fontsize=24, fontweight='bold', va='top', ha='left')

    for i, pc in enumerate(vp['bodies']):
        pc.set_facecolor(face_colors[i])
        pc.set_edgecolor(edge_colors[i])
        pc.set_alpha(0.8)
        
    vp['cmedians'].set_color('black')
    vp['cmedians'].set_linewidth(1.5)

    vp['cbars'].set_color('black')
    vp['cbars'].set_linewidth(1.5)

    vp['cmins'].set_color('black')
    vp['cmins'].set_linewidth(1.5)
    vp['cmaxes'].set_color('black')
    vp['cmaxes'].set_linewidth(1.5)

    for pc in vp2["bodies"]:
        pc.set_facecolor("none")
        #pc.set_edgecolor("none")
        """ pc.set_linewidth(0.5)
        pc.set_linestyle(":") """
    
    vp2['cmedians'].set_color('black')
    vp2['cmedians'].set_linewidth(0.5)
    vp2['cmedians'].set_linestyle(":")

    vp2['cbars'].set_color('black')
    vp2['cbars'].set_linewidth(0.5)
    vp2['cbars'].set_linestyle(":")

    vp2['cmins'].set_color('black')
    vp2['cmins'].set_linewidth(0.5)
    vp2['cmins'].set_linestyle(":")
    vp2['cmaxes'].set_color('black')
    vp2['cmaxes'].set_linewidth(0.5)
    vp2['cmaxes'].set_linestyle(":")

    return ax.get_ylim()

def plot_stacked_bar(ax, data, ylabel, xlabels, ylim_values, label, legend_col_num, position_label=[-0.1,1.1]):
    group_count = len(data)
    bar_width = 0.8
    cumulative = np.zeros(group_count)
    
    data_index = list(range(data.shape[0]))

    cmap = plt.get_cmap("YlGnBu")
    num_colors = 8
    colors = [cmap(i / (num_colors - 1)) for i in range(num_colors)[::-1]]

    for i, column in enumerate(data.columns):
        ax.bar(data_index, data[column], bottom=cumulative, width=bar_width, label=column, color = colors[i], edgecolor = "black", linewidth = 0.5)
        cumulative += data[column]

    ax.set_xticks(data_index)
    ax.set_xticklabels(xlabels)

    ax.text(position_label[0], position_label[1], label, transform=ax.transAxes,
            fontsize=24, fontweight='bold', va='top', ha='left')

    ax.set_xlabel('Products')
    ax.set_ylabel(ylabel)
    if ylim_values:
        ax.set_ylim(ylim_values)

    handles, labels = ax.get_legend_handles_labels()
    handles = handles[::-1]
    labels = ["Transport", "Protein separation electricity", "Protein separation heat", "Protein separation others", "Defatting", "Milling", "Pre-treatment", "Cultivation"]
    ax.legend(handles, labels, loc="upper right", ncols=legend_col_num, frameon=True)
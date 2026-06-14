import pandas as pd
import numpy as np

# Goal is to avoid timestamp differences to cause issues with correlation calculations.  
# 3 minute average will be calculated, extra datas mean will be used. Longer intervals will use same value for the entire interval. 
# If item values stay the same, items will be discarded.
def data_prep(): 
    df = pd.read_parquet("data.parquet") ### Will become dynamic 

    df["clock"] = pd.to_datetime(df["clock"], unit="s")

    df_wide = df.pivot_table(index="clock", columns="name", values="value", aggfunc="mean")

    df_wide = (df_wide.resample("3min").mean().ffill().fillna(0))

    return df_wide

# Goal is to calculate the correlation between items.
# Correlation between same items will be discarded.
def current_corr(df: pd.DataFrame):
    
    pivot_df_clean = df.loc[:, df.nunique() > 1]
    corr_matrix = pivot_df_clean.corr(method='pearson')

    
    return corr_matrix

def corr_to_pairs(corr_matrix: pd.DataFrame):

    corr_matrix = corr_matrix.copy()
    corr_matrix.index.name = None
    corr_matrix.columns.name = None

    # Get upper triangle INCLUDING proper indexing
    mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)

    corr_long = corr_matrix.where(mask).stack().reset_index()

    corr_long.columns = ["First Item", "Second Item", "Corr Value"]

    # safety cleanup (important)
    corr_long = corr_long.dropna(subset=["Corr Value"])

    # now sorting happens AFTER lower triangle is removed
    corr_long = corr_long.sort_values(
        by="Corr Value",
        key=lambda x: x.abs(),
        ascending=False
    )

    return corr_long


if __name__ == "__main__":

    prepped_df = data_prep()
    corr_matrix = current_corr(prepped_df)
    clean_df = corr_to_pairs(corr_matrix)
    
    # Export to Excel
    output_filename = 'correlation_analysis.xlsx'
    
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        clean_df.to_excel(writer, sheet_name='Cross Correlation')

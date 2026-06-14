Zabbix Correlation Tool

A desktop application for exporting historical data from Zabbix, storing the results in Parquet format, performing correlation analysis, and exporting the results to Excel.

Features
Connects to a Zabbix instance using API authentication
Retrieves host and item information from Zabbix
Pulls historical data directly from PostgreSQL
Exports collected data to Parquet format
Automatically locates exported Parquet files
Performs Pearson correlation analysis between items
Resamples data into 3-minute intervals for consistent time alignment
Removes constant-value items from analysis
Sorts correlation results by absolute correlation strength
Exports correlation results to Excel
Automatically removes temporary Parquet files after correlation processing
User-friendly graphical interface built with CustomTkinter

Installation

Clone the repository:

git clone https://github.com/baturalpakyuz/Zabbix-Value-Correlation.git
cd Zabbix-Value-Correlation

Create a virtual environment:

python -m venv venv

Activate the virtual environment:

Windows
venv\Scripts\activate

Linux
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Running the Application

Start the application:

python zabbix_tool.py
Usage
Export Data
Enter the Zabbix URL.
Enter the API token.
Enter PostgreSQL connection details.
Select a start date and time.
Select an end date and time.
Choose an output directory.
Click Continue.

The application will:

Retrieve hosts from Zabbix
Pull historical data from PostgreSQL
Export data into a Parquet file
Run Correlation Analysis

After export is complete:

Click Run Correlation.
The application will:
Load the exported Parquet file
Resample values into 3-minute intervals
Forward-fill missing values
Remove constant-value items
Calculate Pearson correlations
Convert the correlation matrix into item pairs
Sort by absolute correlation value
Export results to Excel

The resulting file:

correlation_analysis.xlsx will be saved in the same directory as the generated Parquet file.

The temporary Parquet file is automatically deleted after successful processing.

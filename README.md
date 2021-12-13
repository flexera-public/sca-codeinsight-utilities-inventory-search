# Code Insight v7 Inventory Keyword Search Script

This python script allows users to query their Code Insight v7 system and obtain a list of all projects potentially impacted by the Log4j security vulnerability ([CVE-2021-44228](https://nvd.nist.gov/vuln/detail/CVE-2021-44228)) along with a listing of all potentially impacted inventory items using a multi keyword search.

## Prerequisites
The following prerequisites are requried to run this script:
 - Code Insight v7 installation
 - Code Insight administrator user access token
 - Python v.3.5 or later

## Script Configuration
In [inventory_search.py](inventory_search.py) please update the following variables:

```python
codeInsightURL = "http://code_insight_server_host_name:port"
adminAuthToken = "*****"
searchTerms = "enter a comma separated list; default values have been provided"
```

## Running the Script
To run the script open a shell or command prompt and run the following command:

```python
python(3) inventory_search.py
```

## Script Output

The script will generate the following output files:
 - ***_inventory_search.log***: a log of the script execution
 - ***inventory_search_results.csv***: a comma separated data file that can be opened in Excel for filtering, sorting, and annotating. The following fields are written to the data file: ***Project Name***, ***Project Contact***, ***Inventory Item***, ***Inventory URL***.

## License
[MIT](LICENSE.TXT)

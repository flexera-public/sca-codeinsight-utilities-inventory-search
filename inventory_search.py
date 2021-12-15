'''
Copyright 2021 Flexera Software LLC
See LICENSE.TXT for full license text
SPDX-License-Identifier: MIT

Author : sgeary  
Created On : Mon Dec 13 2021
File : inventory_search.py
'''
import sys
import os
import logging
import requests
import csv

codeInsightURL = "http://code_insight_server_host_name:port"
adminAuthToken = "*****"

searchTerms = ["druid", "dubbo", "elasticsearch", "flink", "flume", "kafka", "log4j", "logstash", "solr", "struts"]
resultsFileName = "inventory_search_results.csv"

###################################################################################
# Test the version of python to make sure it's at least the version the script
# was tested on, otherwise there could be unexpected results
if sys.version_info <= (3, 5):
    raise Exception("The current version of Python is less than 3.5 which is unsupported.\n Script created/tested against python version 3.8.1. ")
else:
    pass

logfileName = os.path.join(os.path.dirname(os.path.realpath(__file__)),"_inventory_search.log")

###################################################################################
#  Set up logging handler to allow for different levels of logging to be capture
logging.basicConfig(format='%(asctime)s,%(msecs)-3d  %(levelname)-8s [%(filename)-30s:%(lineno)-4d]  %(message)s', datefmt='%Y-%m-%d:%H:%M:%S', filename=logfileName, filemode='w',level=logging.DEBUG)
logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Disable logging for requests module

#----------------------------------------------------------------------#
def main():
    resultsHits = []
    numTotalInventoryItems = 0
    skippedProjects = []
    projectContacts = {}
    projectIndex = 1

    print("Collecting project listing")
    logger.debug("Collecting project listing")

    # Collect a list of projects within the system
    projects = get_projects_listing(codeInsightURL, adminAuthToken)
    numProjects = len(projects)

    # Cycle through each project
    for project in projects:
        projectName = project["name"]
        projectID = project["id"]
        projectContact = project["owner"]
        
        print("")
        print("Examining project %s  --  Project %s of %s" %(projectName, projectIndex, numProjects))
        logger.debug("Examining project %s  --  Project %s of %s" %(projectName, projectIndex, numProjects))
        # Get email address for owner
        if projectContact in projectContacts:
            projectContactEmail = projectContacts[projectContact]
        else:
            logger.debug("    Searching for email address for project contact: %s" %projectContact)
            contactDetails = get_user_by_login(projectContact, codeInsightURL, adminAuthToken)
            projectContactEmail = contactDetails[0]["email"]
            projectContacts[projectContact] = projectContactEmail

        print("    Collecting inventory summary")

        inventoryItems = get_all_project_inventory(codeInsightURL, projectID, adminAuthToken)
        numTotalInventoryItems += len(inventoryItems)

        if "Error" in inventoryItems:
            logger.error("    *** Error collecting project inventory information")
            print("        *** Error collecting project inventory information")
            print("            *** %s" %inventoryItems["Error"])
            skippedProjects.append(projectName)
        else:
            
            print("    Searching inventory items for components containing search terms")
            for inventoryItem in inventoryItems:
                inventoryItemName = inventoryItem["name"]
                componentName = inventoryItem["componentName"]
                inventoryID = inventoryItem["id"]

                validFinding = False

                inventoryItemURL = codeInsightURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectID) + "&tab=projectInventory&pinv=" + str(inventoryID)

                # Compare to each item in the list
                if any(searchTerm.lower() in inventoryItemName.lower() for searchTerm in searchTerms):
                    # There is a potential match so dig deeper to see if valid match
                    # by determining if the match is before or after a [ which is used
                    # in inventory names with "bundled with", "found in" and "dependency of"

                    bracketPosition = inventoryItemName.lower().find("[")

                    if bracketPosition == -1:
                        # This is a direct inventory item so add it
                        validFinding = True                    
                    else:
                        # The item is included due to something else
                        # Is an item include due to the search term component or is the search
                        # term component brought in because of another item?
                        for searchTerm in searchTerms:
                            
                            searchTermPosition = inventoryItemName.lower().find(searchTerm.lower())
                            
                            if searchTermPosition > bracketPosition:
                                # The search term is before bundled with so it is a valid hit 
                                validFinding = False
                                logger.info("            Not adding %s" %inventoryItemName)
                                break
                            else:
                                validFinding = True
                
                # We have a valid hit to add it to the data for the csv file
                if validFinding:
                    resultsHits.append([projectName, projectContactEmail, inventoryItemName, inventoryItemURL]) 
                    

        projectIndex+=1


    print("")
    print("Creating csv results file: %s" %resultsFileName)
    print("    Total projects searched: %s" %numProjects)
    print("    Total inventory tems: %s" %numTotalInventoryItems)
    print("    Total matching inventory items: %s" %len(resultsHits))
    ###########################################
    # Create an csv file with the results
    with open(resultsFileName, 'w', newline='') as resultsFile:
        filewriter = csv.writer(resultsFile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        filewriter.writerow(['Project Name', 'Project Contact', 'Inventory Item', "Inventory URL"])

        for hit in resultsHits:
            filewriter.writerow(hit)
    
    ###########################################
    # Were there any proejcts skipped?
    if len(skippedProjects):
        print("")
        print("The following project should be manually reviewed due to issues retrieving inventory")

        for project in skippedProjects:
            print("    %s" %project)


#------------------------------------------------------------------------------------------#
def get_projects_listing(baseURL, authToken):
    logger.info("    Entering get_projects_listing")

    RESTAPI_BASEURL = baseURL + "/codeinsight/api/"
    RESTAPI_URL = RESTAPI_BASEURL + "projects/"
    #logger.debug("        RESTAPI_URL: %s" %RESTAPI_URL)
    
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken}  
       
    ##########################################################################   
    # Make the REST API call with the project data           
    try:
        response = requests.get(RESTAPI_URL, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        logger.info("        Projects listing received")
        projectListing = response.json()["data"]
        return projectListing
    elif response.status_code == 400:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Bad Request" %response.status_code )
        response.raise_for_status()
    elif response.status_code == 401:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Unauthorized" %response.status_code )
        response.raise_for_status()   
    elif response.status_code == 404:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Not Found" %response.status_code )
        response.raise_for_status()   
    else: 
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        response.raise_for_status()
        
#------------------------------------------------------------------------------------------#
def get_user_by_login(projectContact, baseURL, authToken):
    logger.info("        Entering get_user_by_login")

    RESTAPI_BASEURL = baseURL + "/codeinsight/api/"
    RESTAPI_URL = RESTAPI_BASEURL + "users/search?login=" + projectContact
    #logger.debug("            RESTAPI_URL: %s" %RESTAPI_URL)
    
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken}  
       
    ##########################################################################   
    # Make the REST API call with the project data           
    try:
        response = requests.get(RESTAPI_URL, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error(error)
        return

    ###############################################################################
    # We at least received a response from Code Insight so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        logger.info("            Contact data received")
        contactData = response.json()["data"]
        return contactData
    elif response.status_code == 400:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Bad Request" %response.status_code )
        response.raise_for_status()
    elif response.status_code == 401:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Unauthorized" %response.status_code )
        response.raise_for_status()   
    elif response.status_code == 404:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Not Found" %response.status_code )
        response.raise_for_status()   
    else: 
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        response.raise_for_status()

#-------------------------------------------------------------------------
def get_all_project_inventory(baseURL, projectID, authToken):
    logger.info("    Entering get_project_inventory_summary")
    
    APIOPTIONS = "&published=ANY"
    RESTAPI_BASEURL = baseURL + "/codeinsight/api/"
    ENDPOINT_URL = RESTAPI_BASEURL + "projects/" + str(projectID) + "/inventorySummary/?offset=" 
    RESTAPI_URL = ENDPOINT_URL + "1" + APIOPTIONS
    #logger.debug("        RESTAPI_URL: %s" %RESTAPI_URL)
    
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + authToken} 
       
    ##########################################################################   
    # Make the REST API call with the project data           
    try:
        response = requests.get(RESTAPI_URL, headers=headers)
    except requests.exceptions.RequestException as error:  # Just catch all errors
        logger.error("        %s" %error)
        return     
    
    ###############################################################################
    # We at least received a response from FNCI so check the status to see
    # what happened if there was an error or the expected data
    if response.status_code == 200:
        logger.info("        Project inventory received")
        projectInventorySummary = response.json()["data"]

        # If there are no inventory items just return
        if not projectInventorySummary:
            return projectInventorySummary
            
        currentPage = response.headers["Current-page"]
        numPages = response.headers["Number-of-pages"]
        nextPage = int(currentPage) + 1

        # Are there more pages of data?
        while int(nextPage) <= int(numPages):
            RESTAPI_URL = ENDPOINT_URL + str(nextPage) + APIOPTIONS
            #logger.debug("            RESTAPI_URL: %s" %RESTAPI_URL)

            try:
                response = requests.get(RESTAPI_URL, headers=headers)
            except requests.exceptions.RequestException as error:  # Just catch all errors
                logger.error("    *** Error collecting additional information from project")   
                logger.error("        %s" %error)
                print("    *** Error collecting additional information from project")   

            if response.status_code == 200:
                logger.info("        Project inventory received: Page %s" %(str(nextPage)))
                nextPage = int(response.headers["Current-page"]) + 1
                projectInventorySummary += response.json()["data"]
            else:
                logger.error("Response code %s - %s" %(response.status_code, response.text))
                return{"Error": "There was an error when attempting to get inventory results from page %s" %(str(nextPage+1))}
  
        return projectInventorySummary

    elif response.status_code == 400:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Bad Request" %response.status_code )
    elif response.status_code == 401:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Unauthorized" %response.status_code )
    elif response.status_code == 404:
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        print("Response code: %s   -  Not Found" %response.status_code )
    else: 
        logger.error("Response code %s - %s" %(response.status_code, response.text))
        return{"Error": "There was an error when attempting to get the first page of the inventory results"}
        
        

#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  
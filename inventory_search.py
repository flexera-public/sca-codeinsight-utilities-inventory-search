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

codeInsightURL = "UPDATE_ME"
adminAuthToken = "UPDATE_ME"

searchTerms = ["druid", "dubbo", "elasticsearch", "flink", "flume", "kafka", "log4j", "logstash", "solr", "struts"]
ignoredProjects = ["PROJECT 1", "PROJECT 2", "PROJECT 3"]  # Projects not to examine for one reason or another

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
        if projectName not in ignoredProjects:

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

            inventoryItems =get_all_project_inventory(codeInsightURL, projectID, adminAuthToken)

            print("    Searching inventory items for components containing search terms")
            for inventoryItem in inventoryItems:
                inventoryItemName = inventoryItem["name"]
                componentName = inventoryItem["componentName"]
                inventoryID = inventoryItem["id"]

                inventoryItemURL = codeInsightURL + "/codeinsight/FNCI#myprojectdetails/?id=" + str(projectID) + "&tab=projectInventory&pinv=" + str(inventoryID)

                # Compare to each item in the list
                if any(searchTerm.lower() in componentName.lower() for searchTerm in searchTerms):
                    # If there is a match add a line to the list
                    resultsHits.append([projectName, projectContactEmail, inventoryItemName, inventoryItemURL])

        else:
            print("***  Ignoring project %s  --  Project %s of %s" %(projectName, projectIndex, numProjects))
            logger.debug("    Ignoring project %s  --  Project %s of %s" %(projectName, projectIndex, numProjects))

        projectIndex+=1



    ###########################################
    # Create an csv file with the results
    with open('inventory_search_results.csv', 'w', newline='') as resultsFile:
        filewriter = csv.writer(resultsFile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        filewriter.writerow(['Project Name', 'Project Contact', 'Inventory Item', "Inventory URL"])

        for hit in resultsHits:
            filewriter.writerow(hit)


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
        logger.error(error)
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
                logger.error(error)
                print("    *** Error collecting additional information from project")   

            if response.status_code == 200:
                logger.info("        Project inventory received: Page %s" %(str(nextPage)))
                nextPage = int(response.headers["Current-page"]) + 1
                projectInventorySummary += response.json()["data"]
            else:
                logger.error("Response code %s - %s" %(response.status_code, response.text))
  
        return projectInventorySummary

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

#----------------------------------------------------------------------#    
if __name__ == "__main__":
    main()  
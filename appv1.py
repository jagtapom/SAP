
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import plotly.express as px

# Constants
BARCLAYS_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Barclays_logo.svg/2560px-Barclays_logo.svg.png"

# Sidebar - Branding
st.sidebar.image(BARCLAYS_LOGO_URL, width=100)
st.sidebar.title("Data Source Configuration")

# Sidebar - Input fields
hostname = st.sidebar.text_input("SAP Hostname (e.g., sap.example.com)")
port = st.sidebar.text_input("Port (e.g., 44300)", value="44300")
username = st.sidebar.text_input("SAP Username")
password = st.sidebar.text_input("SAP Password", type="password")
ssl_verify = st.sidebar.checkbox("Verify SSL Certificates", value=False)

# Function to fetch OData Service Catalog (XML parsing)
def fetch_service_catalog(hostname, port, username, password, ssl_verify):
    catalog_url = f"https://{hostname}:{port}/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/ServiceCollection"
    try:
        response = requests.get(
            catalog_url,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/xml"},
            verify=ssl_verify
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)

        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
            'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices'
        }

        services = []
        for entry in root.findall('atom:entry', namespaces):
            tech_name = entry.find(".//d:TechnicalServiceName", namespaces)
            tech_service_name = entry.find(".//d:TechnicalName", namespaces)
            service_url = entry.find(".//d:ServiceUrl", namespaces)

            if tech_name is not None and tech_service_name is not None and service_url is not None:
                services.append({
                    'TechnicalName': tech_service_name.text,
                    'TechnicalServiceName': tech_name.text,
                    'ServiceUrl': service_url.text
                })

        return services

    except Exception as e:
        st.error(f"Failed to fetch service catalog: {e}")
        return []

# Function to fetch EntitySets from service metadata
def fetch_entitysets(hostname, port, service_name, username, password, ssl_verify):
    metadata_url = f"https://{hostname}:{port}/sap/opu/odata/sap/{service_name}/$metadata"
    try:
        response = requests.get(
            metadata_url,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/xml"},
            verify=ssl_verify
        )
        response.raise_for_status()

        root = ET.fromstring(response.content)
        namespaces = {'edmx': 'http://schemas.microsoft.com/ado/2007/06/edmx',
                      'edm': 'http://schemas.microsoft.com/ado/2008/09/edm'}

        entity_sets = [
            entityset.attrib['Name']
            for entityset in root.findall(".//edm:EntitySet", namespaces)
        ]

        return entity_sets
    except Exception as e:
        st.error(f"Failed to fetch EntitySets: {e}")
        return []

services = []
if hostname and port and username and password:
    services = fetch_service_catalog(hostname, port, username, password, ssl_verify)

service_names = [f"{srv['TechnicalName']} - {srv['TechnicalServiceName']}" for srv in services] if services else []
selected_service = st.sidebar.selectbox("Select OData Service", service_names) if service_names else None

selected_entityset = None
if selected_service:
    selected_service_obj = next((srv for srv in services if srv['TechnicalName'] in selected_service), None)
    if selected_service_obj:
        service_name = selected_service_obj['TechnicalName']
        entity_sets = fetch_entitysets(hostname, port, service_name, username, password, ssl_verify)
        selected_entityset = st.sidebar.selectbox("Select EntitySet", entity_sets) if entity_sets else None

st.title("BW/4HANA OData Data Analysis")

# Function to fetch data from selected OData service
def fetch_service_data(hostname, port, service_name, entity_set, username, password, ssl_verify):
    service_url = f"https://{hostname}:{port}/sap/opu/odata/sap/{service_name}/{entity_set}"
    try:
        response = requests.get(
            service_url,
            auth=HTTPBasicAuth(username, password),
            headers={"Accept": "application/json"},
            verify=ssl_verify
        )
        response.raise_for_status()
        data = response.json()
        df = pd.json_normalize(data['d']['results'])
        return df
    except Exception as e:
        st.error(f"Failed to fetch data from service: {e}")
        return pd.DataFrame()

if selected_service and selected_entityset:
    st.subheader(f"Data from Service: {service_name}, EntitySet: {selected_entityset}")
    df = fetch_service_data(hostname, port, service_name, selected_entityset, username, password, ssl_verify)

    if not df.empty:
        st.write("### Data Table")
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationAutoPageSize=True)
        grid_options = gb.build()

        AgGrid(df, gridOptions=grid_options, height=300)

        st.write("### Data Visualization")
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()

        if len(numeric_columns) >= 2:
            x_axis = st.selectbox("Select X-axis", numeric_columns)
            y_axis = st.selectbox("Select Y-axis", numeric_columns, index=1)

            chart_type = st.selectbox("Select Chart Type", ["Bar", "Line", "Scatter"])

            if chart_type == "Bar":
                fig = px.bar(df, x=x_axis, y=y_axis)
            elif chart_type == "Line":
                fig = px.line(df, x=x_axis, y=y_axis)
            else:
                fig = px.scatter(df, x=x_axis, y=y_axis)

            st.plotly_chart(fig)
        else:
            st.info("Not enough numeric columns available for graphing.")
    else:
        st.warning("No data available to display.")
else:
    st.info("Please provide connection details, select a service, and an EntitySet.")

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
import requests
import plotly.express as px

# Constants
BARCLAYS_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Barclays_logo.svg/2560px-Barclays_logo.svg.png"

# Sidebar
st.sidebar.image(BARCLAYS_LOGO_URL, width=100)
datasource = st.sidebar.selectbox(
    "Select Data Source",
    ("BW4HANA", "Athena", "Redshift")
)

st.title("Data Analysis Platform")

# Function to fetch data from BW4HANA OData
def fetch_bw4hana_data():
    # Placeholder OData URL, replace with actual endpoint
    odata_url = "https://example.com/odata/service"
    try:
        response = requests.get(odata_url)
        response.raise_for_status()
        data = response.json()

        # Flatten and convert JSON to DataFrame - adjust based on actual JSON structure
        df = pd.json_normalize(data['value'])
        return df
    except Exception as e:
        st.error(f"Failed to fetch BW4HANA data: {e}")
        return pd.DataFrame()

# Render content based on selection
if datasource == "BW4HANA":
    st.subheader("BW4HANA OData Data")
    df = fetch_bw4hana_data()

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

            fig = px.bar(df, x=x_axis, y=y_axis, title=f'{y_axis} by {x_axis}')
            st.plotly_chart(fig)
        else:
            st.info("Not enough numeric columns available for graphing.")
    else:
        st.warning("No data available to display.")

elif datasource in ["Athena", "Redshift"]:
    st.subheader(f"{datasource} Integration")
    st.info("This feature is under development.")

else:
    st.error("Invalid data source selection.")

# EuropeOrthoViewer
EuropeOrthoViewer provides organized access to WMS, WMTS, and REST orthophoto services (and other related data) from European countries, making them easier to browse and add to QGIS projects.

## Features
- Access orthophoto services from multiple European countries
- Support for **WMS**, **WMTS**, and **ArcGIS REST** services
- Browse available layers before adding them to your project
- Specify Coordinate Reference System of the layers
- Organized catalog for easier discovery

## Installation
1.  Download files found at [https://github.com/ardatalar/EuropeOrthoViewer)
2.  Convert the folder named EuropeOrthoViewer into a zip
3.  Open up Qgis Desktop 3.0 or higher
4.  From the menu go to **Plugins > Manage and Install Plugins... > Install from ZIP**
5.  Choose the newly created zip file, and click **install**
6.  Once installed, ensure that you have checked **Show also experimental plugins** found at **Plugins > Manage and Install Plugins... > Settings**
7.  Finally, go to **Plugins > Manage and Install Plugins... > Installed** and make sure **EuropeOrthoViewer** is checked

## Usage
- Open QGIS.
- Activate the plugin from the Plugins menu.
- Select a country (if applicable and a region) and list available WMS/WMTS/REST layers.
- (Optional) Specify Coordinate Reference System (Default is EPSG:4326). 
- (Optional) Specify image format.
- Add selected orthophotos or related datasets to your map.
- Selected layer is displayed in the QGIS project.

## Limitations
EuropeOrthoViewer relies on service links provided by the respective national authorities. As a result, data quality, availability, and resolution may vary between countries and can change over time. In addition, data providers may update or discontinue services. Regular verification of the links is therefore required to ensure continued access.

## Credits
- Arda Atalar | TUM, Professorship of Big Geospatial Data Management
- Carla Sophie Rieger | TUM, Professorship of Big Geospatial Data Management
- Giulia De Florio | TUM, Professorship of Big Geospatial Data Management

## License
This plugin is licensed under the **MIT License**. 

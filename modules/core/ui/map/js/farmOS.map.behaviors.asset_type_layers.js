(function (drupalSettings) {
  farmOS.map.behaviors.asset_type_layers = {
    attach: function (instance) {

      const vectorLayers = [];
      const emptyState = instance.farmMapSettings.empty_state;
      let completedLayerLoads = 0;
      let layerLoadFailed = false;

      const showEmptyState = function () {
        if (!emptyState || instance.map.getTargetElement().querySelector('.farm-map__empty-state')) {
          return;
        }

        const state = document.createElement('div');
        state.className = 'farm-map__empty-state';
        state.setAttribute('role', 'status');

        const title = document.createElement('h2');
        title.textContent = emptyState.title;
        state.appendChild(title);

        const message = document.createElement('p');
        message.textContent = emptyState.message;
        state.appendChild(message);

        instance.map.getTargetElement().appendChild(state);
      };

      const finishLayerLoading = function (failed = false) {
        completedLayerLoads++;
        layerLoadFailed = layerLoadFailed || failed;

        if (completedLayerLoads !== vectorLayers.length) {
          return;
        }

        const features = vectorLayers.reduce((count, layer) => count + layer.layer.getSource().getFeatures().length, 0);
        if (features > 0) {
          if (vectorLayers.some((layer) => layer.zoom)) {
            instance.zoomToVectors();
          }
        } else if (!layerLoadFailed) {
          showEmptyState();
        }
      };

      // Check if there are asset type layers to add.
      if (instance.farmMapSettings.asset_type_layers !== undefined) {

        // Add layers for each area type.
        var layers = instance.farmMapSettings.asset_type_layers;

        // Create any layer groups that were explicitly defined. We do this
        // first to ensure that they are available to put asset type layers in.
        // Skip any layers that are not a group.
        Object.values(layers).reverse().forEach( layer => {

          // If the layer is not a group, skip it.
          if (!layer.is_group) {
            return;
          }

          // Add the layer group.
          var opts = {
            title: layer.label,
          }
          if (!!layer.group) {
            opts.group = layer.group;
          }
          instance.addLayer('group', opts);
        });


        // Add each asset type layer.
        Object.values(layers).reverse().forEach( layer => {

          // If the layer is a group, skip it.
          if (!!layer.is_group) {
            return;
          }

          // Determine if the layer should display full geometry or centroids.
          let geomType = 'full';
          let layerType = 'geojson';
          if (!!layer.cluster && layer.cluster) {
            geomType = 'centroid';
            layerType = 'cluster';
          }

          // Build a url to the asset type geojson, default to all.
          const assetType = layer.asset_type || 'all';
          const url = new URL('assets/geojson/' + geomType + '/' + assetType, window.location.origin + drupalSettings.path.baseUrl);

          // Include provided filters.
          const filters = layer.filters || {};
          Object.entries(filters).forEach( ([key, value]) => {
            if (Array.isArray(value)) {
              for (let i = 0; i < value.length; i++) {
                url.searchParams.append(key + '[]', value[i]);
              }
            }
            else {
              url.searchParams.append(key, value);
            }
          });

          // Build the layer.
          var opts = {
            title: layer.label,
            url,
            color: layer.color,
          };

          // Add the group if specified.
          if (!!layer.group) {
            opts.group = layer.group;
          }

          var newLayer = instance.addLayer(layerType, opts);

          // Track geometry sources so that maps zoom to the combined extent
          // once all asset layers have loaded and can show a useful empty state.
          if (layerType === 'geojson' || layerType === 'cluster') {
            vectorLayers.push({
              layer: newLayer,
              zoom: layerType !== 'cluster' && layer.zoom === true,
            });
          }
        });
      }

      if (vectorLayers.length === 0) {
        showEmptyState();
      } else {
        vectorLayers.forEach(function (layer) {
          const source = layer.layer.getSource();
          source.once('featuresloadend', function () {
            finishLayerLoading();
          });
          source.once('featuresloaderror', function () {
            finishLayerLoading(true);
          });
        });
      }

      // Load area details via AJAX when an area popup is displayed.
      instance.popup.on('farmOS-map.popup', function (event) {
        var link = event.target.element.querySelector('.ol-popup-name a');
        if (link) {
          var assetLink = link.getAttribute('href')
          var description = event.target.element.querySelector('.ol-popup-description');

          // Add loading text.
          var loading = document.createTextNode('Loading asset details...');
          description.appendChild(loading);

          // Create an iframe linking to the map_popup view mode.
          var frame = document.createElement('iframe');
          frame.setAttribute('src', assetLink + '/map-popup');
          frame.onload = function () {
            description.removeChild(loading);
            instance.popup.panIntoView();
          }
          description.appendChild(frame);
        }
      });
    }
  };
}(drupalSettings));

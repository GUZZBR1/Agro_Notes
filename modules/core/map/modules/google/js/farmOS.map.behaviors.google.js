(function (drupalSettings) {
  farmOS.map.behaviors.google = {
    attach: function (instance) {
      var key = drupalSettings.farm_map.behaviors.google.api_key;
      this.addGoogleLayer(instance, key, 'Google Roadmap', 'roadmap');
      this.addGoogleLayer(instance, key, 'Google Terrain', 'terrain', ['layerRoadmap']);
      this.addGoogleLayer(instance, key, 'Google Satellite', 'satellite', ['layerRoadmap'],true);
    },
    addGoogleLayer: function (instance, key, title, mapType, layerTypes = [], visible = false) {
      instance.addLayer('google', {
        title: title,
        mapType: mapType,
        layerTypes: layerTypes,
        key: key,
        group: 'Base layers',
        base: true,
        visible: visible,
      });
    }
  };
}(drupalSettings));

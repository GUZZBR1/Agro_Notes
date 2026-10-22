<?php

declare(strict_types=1);

namespace Drupal\farm_ui_map\EventSubscriber;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_map\Event\MapRenderEvent;
use Drupal\farm_map\LayerStyleLoaderInterface;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

/**
 * An event subscriber for the MapRenderEvent.
 *
 * Adds the wkt and geofield behaviors to necessary maps.
 */
class MapRenderEventSubscriber implements EventSubscriberInterface {

  use StringTranslationTrait;

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
    protected LayerStyleLoaderInterface $layerStyleLoader,
  ) {}

  /**
   * {@inheritdoc}
   */
  public static function getSubscribedEvents(): array {
    return [
      MapRenderEvent::EVENT_NAME => 'onMapRender',
    ];
  }

  /**
   * React to the MapRenderEvent.
   *
   * @param \Drupal\farm_map\Event\MapRenderEvent $event
   *   The MapRenderEvent.
   */
  public function onMapRender(MapRenderEvent $event) {

    // Location and asset list maps need an explanation when there are no
    // geometries to display. Keep this off maps used for editing geometry or
    // the dashboard.
    if (in_array($event->getMapType()->id(), ['locations', 'asset_list'])) {
      $settings[$event->getMapTargetId()]['empty_state'] = [
        'title' => $this->t('No locations to show yet'),
        'message' => $this->t('Add a location asset or draw a boundary to see it on this map. Use the Add location action above.'),
      ];
      $event->addSettings($settings);
    }

    // Add behaviors/settings to default and geofield maps.
    if (in_array($event->getmapType()->id(), ['default', 'geofield'])) {

      // Add "All locations" layers.
      $event->addBehavior('asset_type_layers');
      $settings[$event->getMapTargetId()]['asset_type_layers']['all_locations'] = [
        'label' => $this->t('All locations'),
        'filters' => [
          'is_location' => 1,
        ],
        'color' => 'grey',
        'zoom' => TRUE,
      ];
      $event->addSettings($settings);

      // Prevent zooming to the "All locations" layer if WKT is provided.
      if (!empty($event->element['#map_settings']['wkt'])) {
        $settings[$event->getMapTargetId()]['asset_type_layers']['all_locations']['zoom'] = FALSE;
        $event->addSettings($settings);
      }
    }

    // If the "locations" behavior is added to the map, add layers for each
    // location asset type.
    if (in_array('locations', $event->getMapBehaviors())) {

      $layers = [];

      // Define common layer properties.
      $group = $this->t('Locations');
      $filters = [
        'is_location' => 1,
      ] + ($event->element['#location_filters'] ?? []);

      // Add separate layers for all asset types that are locations by default.
      $other_location_asset_types = [];
      $asset_types = $this->entityTypeManager->getStorage('asset_type')->loadMultiple();
      foreach ($asset_types as $type) {

        // Add a dedicated layer if the asset type is a location by default.
        if ($type->getThirdPartySetting('farm_location', 'is_location', FALSE)) {

          // Load the map layer style.
          /** @var \Drupal\farm_map\Entity\LayerStyleInterface|null $layer_style */
          if ($layer_style = $this->layerStyleLoader->load(['asset_type' => $type->id()])) {
            $color = $layer_style->get('color');
          }

          // Add layer for the asset type.
          $layers[$type->id()] = [
            'group' => $group,
            'label' => $type->label(),
            'asset_type' => $type->id(),
            'filters' => $filters,
            'color' => $color ?? 'orange',
            'zoom' => TRUE,
          ];
        }
        // Else save the asset type for the "Other locations" layer.
        else {
          $other_location_asset_types[] = $type->id();
        }
      }

      // Add a layer of location assets of other asset types.
      if (count($other_location_asset_types)) {
        $layers['other_locations'] = [
          'group' => $group,
          'label' => $this->t('Other locations'),
          'filters' => $filters + ['type' => $other_location_asset_types],
          'color' => 'orange',
          'zoom' => TRUE,
        ];
      }

      // Add the asset_type_layers behavior.
      $event->addBehavior('asset_type_layers');

      // Add map specific settings.
      $settings[$event->getMapTargetId()]['asset_type_layers'] = $layers;
      $event->addSettings($settings);
    }
  }

}

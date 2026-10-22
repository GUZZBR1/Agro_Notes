<?php

declare(strict_types=1);

namespace Drupal\farm_land\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_land\Entity\FarmLandType;
use Drupal\farm_map\LayerStyleLoaderInterface;
use Drupal\views\ViewExecutable;

/**
 * Views execution hook implementations for farm_land.
 */
class ViewsExecutionHooks {

  use StringTranslationTrait;

  public function __construct(
    protected LayerStyleLoaderInterface $layerStyleLoader,
  ) {}

  /**
   * Implements hook_views_pre_render().
   */
  #[Hook('views_pre_render')]
  public function viewsPreRender(ViewExecutable $view) {

    // Add land type map layers to the land assets map.
    if ($view->id() == 'farm_asset' && $view->current_display == 'page_type' && !empty($view->args[0]) && $view->args[0] == 'land') {

      // If the asset_map has not been added, bail.
      if (empty($view->attachment_before['asset_map'])) {
        return;
      }
      $map =& $view->attachment_before['asset_map'];

      // Load all land types.
      $land_types = FarmLandType::loadMultiple();

      // Get exposed filters.
      $exposed_filters = $view->getExposedInput();

      // If the land type exposed filter is already in use remove land types
      // that are not specified by the filter value.
      if (isset($exposed_filters['land_type_value'])) {
        $land_type_filters = (array) $exposed_filters['land_type_value'];
        $land_types = array_intersect_key($land_types, $land_type_filters);
      }

      // Create a layer for each land type.
      $asset_layers = [];
      foreach ($land_types as $land_type) {
        if ($layer_style = $this->layerStyleLoader->load(['asset_type' => 'land', 'land_type' => $land_type->id()])) {
          $color = $layer_style->get('color');
        }
        $asset_layers['land_' . $land_type->id()] = [
          'group' => $this->t('Land types'),
          'label' => $land_type->label(),
          'asset_type' => 'land',
          'filters' => $exposed_filters + [
            'land_type_value[]' => $land_type->id(),
          ],
          'color' => $color ?? 'orange',
          'zoom' => TRUE,
        ];
      }

      // Add layers to the map settings.
      $map['#map_settings']['asset_type_layers'] = array_merge($map['#map_settings']['asset_type_layers'], $asset_layers);

      // Remove the land asset layer.
      unset($map['#map_settings']['asset_type_layers']['full_land']);
    }
  }

}

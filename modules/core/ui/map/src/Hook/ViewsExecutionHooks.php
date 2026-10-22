<?php

declare(strict_types=1);

namespace Drupal\farm_ui_map\Hook;

use Drupal\Core\Entity\EntityFieldManagerInterface;
use Drupal\Core\Entity\EntityTypeBundleInfoInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Hook\Order\Order;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\asset\Entity\AssetType;
use Drupal\farm_map\LayerStyleLoaderInterface;
use Drupal\farm_ui_views\FarmUiViewsHelper;
use Drupal\views\Entity\View;
use Drupal\views\ViewExecutable;

/**
 * Views execution hook implementations for farm_ui_map.
 */
class ViewsExecutionHooks {

  use StringTranslationTrait;

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
    protected EntityFieldManagerInterface $entityFieldManager,
    protected EntityTypeBundleInfoInterface $entityTypeBundleInfo,
    protected ModuleHandlerInterface $moduleHandler,
    protected LayerStyleLoaderInterface $layerStyleLoader,
  ) {}

  /**
   * Implements hook_views_pre_view().
   */
  #[Hook('views_pre_view')]
  public function viewsPreView(ViewExecutable $view, $display_id, array &$args) {

    // Alter the farm_asset_geojson View's full and centroid displays to add all
    // exposed filters that are present in the farm_asset View.
    if ($view->id() == 'farm_asset_geojson' && in_array($display_id, ['full', 'centroid'])) {

      // Add filter handlers for base fields provided by other modules.
      $base_fields = $this->moduleHandler->invokeAll('farm_ui_views_base_fields', [$view->getBaseEntityType()->id()]);
      foreach ($this->entityFieldManager->getBaseFieldDefinitions($view->getBaseEntityType()->id()) as $field_definition) {
        if (!in_array($field_definition->getName(), $base_fields)) {
          continue;
        }
        FarmUiViewsHelper::addHandlers($view, $display_id, 'filter', $field_definition);
      }

      // Load the farm_asset View. Bail if unavailable.
      $farm_asset_view = View::load('farm_asset');
      if (empty($farm_asset_view)) {
        return;
      }

      // Copy all exposed filters from the default display.
      $display = $farm_asset_view->getDisplay('default');
      if (!empty($display['display_options']['filters'])) {
        foreach ($display['display_options']['filters'] as $field => $filter) {
          $view->addHandler($display_id, 'filter', $filter['table'], $field, $filter, $filter['id']);
        }
      }

      // If a type argument is present, add bundle-specific exposed filters.
      if (!empty($args[0]) && $args[0] != 'all' && array_key_exists($args[0], $this->entityTypeBundleInfo->getBundleInfo($view->getBaseEntityType()->id()))) {
        /** @var \Drupal\entity\BundleFieldDefinition[] $bundle_fields */
        $bundle_fields = $this->entityTypeManager->getHandler($view->getBaseEntityType()->id(), 'bundle_plugin')->getFieldDefinitions($args[0]);
        foreach (array_reverse($bundle_fields) as $field_definition) {
          FarmUiViewsHelper::addHandlers($view, $display_id, 'filter', $field_definition);
        }
      }
    }
  }

  /**
   * Implements hook_views_pre_render().
   *
   * Ensure this module's implementation runs first.
   */
  #[Hook('views_pre_render', order: Order::First)]
  public function viewsPreRender(ViewExecutable $view) {

    // Render a map attachment above views of assets.
    if ($view->id() == 'farm_asset' && in_array($view->current_display, ['page', 'page_type'])) {

      // Get all asset bundles.
      $asset_bundles = $this->entityTypeBundleInfo->getBundleInfo($view->getBaseEntityType()->id());

      // Start array of filtered bundles.
      $filtered_bundles = $asset_bundles;

      // Start array of asset layers to add.
      $asset_layers = [
        'full' => [],
      ];

      // Save the group labels.
      $layer_group = $view->getBaseEntityType()->getCollectionLabel();

      // Get exposed filters.
      /** @var array<string,string[]> $exposed_filters */
      $exposed_filters = $view->getExposedInput();

      // Add multiple asset layers to the page of all assets.
      if ($view->current_display == 'page') {

        // Limit to filtered asset types.
        if (!empty($exposed_filters['type'])) {
          $filtered_bundles = array_intersect_key($asset_bundles, array_flip($exposed_filters['type']));
        }
      }

      // Determine if we are filtering by bundle.
      // This may happen via contextual filter on the "page_type" display, or
      // via the exposed "type" filter.
      $bundle_filters = [];
      if ($view->current_display == 'page_type' && !empty($view->args[0])) {
        $bundle_filters[] = $view->args[0];
      }
      elseif (!empty($exposed_filters['type'])) {
        foreach ($exposed_filters['type'] as $bundle) {
          $bundle_filters[] = $bundle;
        }
      }

      // Filter by bundle, if desired.
      if (!empty($bundle_filters)) {
        $filtered_bundles = [];
        foreach ($bundle_filters as $bundle) {
          $filtered_bundles[$bundle] = $asset_bundles[$bundle];
        }
      }

      // Add a cluster layer for summarizing asset counts.
      $asset_layers['cluster']['all'] = [
        'label' => $this->t('Asset counts'),
        'cluster' => TRUE,
        'filters' => $exposed_filters,
      ];
      if (!empty($bundle_filters)) {
        $asset_layers['cluster']['all']['asset_type'] = implode('+', $bundle_filters);
      }

      // Add a full asset geometry layer for each asset type.
      foreach ($filtered_bundles as $bundle => $bundle_info) {

        // Load the bundle entity.
        $type = AssetType::load($bundle);

        // Load the map layer style.
        if ($layer_style = $this->layerStyleLoader->load(['asset_type' => $bundle])) {
          $color = $layer_style->get('color');
        }

        // Add layer for the asset type.
        $asset_layers['full']['full_' . $bundle] = [
          'group' => $type->getThirdPartySetting('farm_location', 'is_location', FALSE) ? $this->t('Location assets') : $layer_group,
          'label' => $bundle_info['label'],
          'asset_type' => $bundle,
          'filters' => $exposed_filters,
          'color' => $color ?? 'orange',
          'zoom' => TRUE,
        ];
      }

      // Build the map render array.
      $map = [
        '#type' => 'farm_map',
        '#map_type' => 'asset_list',
      ];
      $all_layers = array_merge($asset_layers['cluster'], $asset_layers['full']);
      $map['#map_settings']['asset_type_layers'] = $all_layers;

      // Render the map.
      $view->attachment_before['asset_map'] = $map;
    }
  }

}

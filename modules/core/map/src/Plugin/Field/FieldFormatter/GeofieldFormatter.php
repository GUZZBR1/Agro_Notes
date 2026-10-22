<?php

declare(strict_types=1);

namespace Drupal\farm_map\Plugin\Field\FieldFormatter;

use Drupal\Core\Field\Attribute\FieldFormatter;
use Drupal\Core\Field\FieldDefinitionInterface;
use Drupal\Core\Field\FieldItemListInterface;
use Drupal\Core\Field\FormatterBase;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\geofield\GeoPHP\GeoPHPInterface;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Plugin implementation of the map 'geofield' formatter.
 */
#[FieldFormatter(
  id: 'farm_map_geofield',
  label: new TranslatableMarkup('farmOS Map'),
  field_types: ['geofield'],
)]
class GeofieldFormatter extends FormatterBase {

  public function __construct(
    $plugin_id,
    $plugin_definition,
    FieldDefinitionInterface $field_definition,
    array $settings,
    $label,
    $view_mode,
    array $third_party_settings,
    protected GeoPHPInterface $geoPhp,
  ) {
    parent::__construct($plugin_id, $plugin_definition, $field_definition, $settings, $label, $view_mode, $third_party_settings);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    // @todo Use autowiring and remove this when the parent class does.
    // @see https://www.drupal.org/project/drupal/issues/3552110
    return new static(
      $plugin_id,
      $plugin_definition,
      $configuration['field_definition'],
      $configuration['settings'],
      $configuration['label'],
      $configuration['view_mode'],
      $configuration['third_party_settings'],
      $container->get('geofield.geophp'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function viewElements(FieldItemListInterface $items, $langcode) {

    // Build a render element.
    $element = [];

    // First check to see if we have any value and remove any unset deltas.
    foreach ($items as $delta => $item) {
      if (empty($item->get('value')->getValue())) {
        unset($items[$delta]);
      }
    }

    // If there are no items, stop here. We won't show anything.
    if ($items->isEmpty()) {
      return $element;
    }

    // Create array of features.
    $features = [];
    foreach ($items as $delta) {

      // Get the field value.
      $value = $delta->get('value')->getValue();

      // Convert to WKT.
      $geom = $this->geoPhp->load($value);
      $features[] = $geom->out('wkt');
    }

    // If there are no features at this point, bail.
    if (empty($features)) {
      return $element;
    }

    // Build a map for each item.
    foreach ($features as $delta => $feature) {
      $element[$delta] = [
        '#type' => 'farm_map',
        '#map_type' => 'geofield',
        '#map_settings' => [
          'wkt' => $feature,
          'behaviors' => [
            'wkt' => [
              'zoom' => TRUE,
            ],
          ],
        ],
      ];
    }

    return $element;
  }

}

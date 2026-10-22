<?php

declare(strict_types=1);

namespace Drupal\farm_material\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\quantity\Entity\QuantityInterface;

/**
 * Entity hook implementations for farm_material.
 */
class EntityHooks {

  /**
   * Implements hook_ENTITY_TYPE_presave().
   */
  #[Hook('quantity_presave')]
  public function quantityPresave(QuantityInterface $quantity) {

    // Bail if not a material quantity.
    if ($quantity->bundle() !== 'material') {
      return;
    }

    // Bail if there is no inventory field or if it is empty.
    if (!$quantity->hasField('inventory_asset') || $quantity->get('inventory_asset')->isEmpty()) {
      return;
    }

    // Get the referenced inventory asset.
    /** @var \Drupal\asset\Entity\AssetInterface[] $assets */
    $assets = $quantity->get('inventory_asset')->referencedEntities();
    $asset = reset($assets);

    // Bail if not a material asset.
    if (empty($asset) || $asset->bundle() !== 'material') {
      return;
    }

    // Copy the material asset material_type field to the material quantity.
    if (!$asset->get('material_type')->isEmpty()) {
      $material_type = $asset->get('material_type')->getValue();
      $quantity->set('material_type', $material_type);
    }
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_location\Field;

use Drupal\Core\Field\FieldItemList;
use Drupal\Core\TypedData\ComputedItemListTrait;
use Drupal\asset\Entity\AssetInterface;

/**
 * Computes the current geometry value for assets.
 */
class AssetGeometryItemList extends FieldItemList {

  use ComputedItemListTrait;

  /**
   * Computes the current geometry value for the asset.
   */
  protected function computeValue() {

    // Get the asset entity.
    $entity = $this->getEntity();

    // Get the asset geometry.
    assert($entity instanceof AssetInterface);
    $geometry = \Drupal::service('asset.location')->getGeometry($entity);

    // Update the assets current geometry value to match.
    // @todo Cache this field computation.
    $this->list[0] = $this->createItem(0, $geometry);
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Access;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Routing\Access\AccessInterface;
use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Checks access for displaying Views of inventory quantities for an asset.
 */
class FarmInventoryAssetViewsAccessCheck implements AccessInterface {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * A custom access check.
   *
   * @param \Drupal\Core\Routing\RouteMatchInterface $route_match
   *   The route match.
   */
  public function access(RouteMatchInterface $route_match) {

    // Get the "asset" parameter and attempt to load the asset.
    // If the asset cannot be loaded, allow access so that Views contextual
    // filter validation returns a 404.
    $asset_id = $route_match->getParameter('asset');
    /** @var \Drupal\asset\Entity\AssetInterface|null $asset */
    $asset = $this->entityTypeManager->getStorage('asset')->load($asset_id);
    if (is_null($asset)) {
      return AccessResult::allowed();
    }

    // Allow access if the asset has an inventory.
    $access = AccessResult::allowedIf($asset->hasField('inventory') && !$asset->get('inventory')->isEmpty());

    // Invalidate the access result when the asset is changed.
    $access->addCacheTags($asset->getCacheTags());
    return $access;
  }

}

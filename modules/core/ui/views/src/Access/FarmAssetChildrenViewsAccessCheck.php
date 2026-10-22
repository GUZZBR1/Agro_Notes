<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Access;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Routing\Access\AccessInterface;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\farm_location\AssetLocationInterface;

/**
 * Checks access for displaying Views of asset children.
 */
class FarmAssetChildrenViewsAccessCheck implements AccessInterface {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
    protected AssetLocationInterface $assetLocation,
  ) {}

  /**
   * A custom access check.
   *
   * @param \Drupal\Core\Routing\RouteMatchInterface $route_match
   *   The route match.
   */
  public function access(RouteMatchInterface $route_match) {

    // Get asset storage.
    $asset_storage = $this->entityTypeManager->getStorage('asset');

    // Get the "asset" parameter and attempt to load the asset.
    // If the asset cannot be loaded, allow access so that Views contextual
    // filter validation returns a 404.
    $asset_id = $route_match->getParameter('asset');
    /** @var \Drupal\asset\Entity\AssetInterface|null $asset */
    $asset = $asset_storage->load($asset_id);
    if (is_null($asset)) {
      return AccessResult::allowed();
    }

    // If the asset is a location, deny access.
    // The farm_ui_location module provides a Locations tab for child locations.
    if ($this->assetLocation->isLocation($asset)) {
      return AccessResult::forbidden();
    }

    // Run a count query to see if there are any assets that reference this
    // asset as a parent.
    $count = $asset_storage->getAggregateQuery()
      ->accessCheck(TRUE)
      ->condition('parent.entity.id', $asset_id)
      ->count()
      ->execute();

    // Determine access based on the child count.
    $access = AccessResult::allowedIf($count > 0);

    // Invalidate the access result when assets are changed.
    $access->addCacheTags(["asset_list"]);
    return $access;
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_group\Access;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Routing\Access\AccessInterface;
use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Checks access for displaying Views of group members.
 */
class FarmGroupMembersViewsAccessCheck implements AccessInterface {

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

    // If there is no "asset" parameter, bail.
    $asset_id = $route_match->getParameter('asset');
    if (empty($asset_id)) {
      return AccessResult::allowed();
    }

    // Load the asset.
    $asset_storage = $this->entityTypeManager->getStorage('asset');
    /** @var \Drupal\asset\Entity\AssetInterface $asset */
    $asset = $asset_storage->load($asset_id);

    // Allow access if the asset is a group.
    $access = AccessResult::allowedIf($asset->bundle() == 'group');

    // Invalidate the access result when assets are changed.
    $access->addCacheTags(["asset_list"]);
    return $access;
  }

}

<?php

declare(strict_types=1);

namespace Drupal\farm_location\Plugin\views\argument;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\farm_location\AssetLocationInterface;
use Drupal\views\Attribute\ViewsArgument;
use Drupal\views\Plugin\views\argument\ArgumentPluginBase;
use Drupal\views\Plugin\views\query\Sql;

/**
 * An argument for filtering assets by their current location.
 *
 * @ingroup views_argument_handlers
 */
#[ViewsArgument("asset_location")]
class AssetLocation extends ArgumentPluginBase {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    protected EntityTypeManagerInterface $entityTypeManager,
    protected AssetLocationInterface $assetLocation,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition);
  }

  /**
   * {@inheritdoc}
   */
  public function query($group_by = FALSE) {

    // Bail if not a SQL query.
    if (!$this->query instanceof Sql) {
      return;
    }

    // Load the location asset, and bail if it's null.
    /** @var \Drupal\asset\Entity\AssetInterface|null $location */
    $location = $this->entityTypeManager->getStorage('asset')->load($this->argument);
    if (is_null($location)) {
      return;
    }

    // First query for a list of asset IDs in the location, then use this list
    // to filter the current View.
    // We do this in two separate queries for a few reasons:
    // 1. The Drupal and Views query APIs do not support the kind of compound
    // JOIN that we use in the asset.location service's getAssetsByLocation().
    // 2. We need to allow other modules to override the asset.location service
    // to provide their own location logic (eg: the Group asset module). They
    // shouldn't have to override this Views argument handler as well.
    // 3. It keeps this Views argument handler's query modifications very
    // simple. It only needs the condition: "WHERE asset.id IN (:asset_ids)".
    // See https://www.drupal.org/project/farm/issues/3217168 for more info.
    $assets = $this->assetLocation->getAssetsByLocation([$location]);
    $asset_ids = [];
    foreach ($assets as $asset) {
      $asset_ids[] = $asset->id();
    }

    // If there are no asset IDs, add 0 to ensure the array is not empty.
    if (empty($asset_ids)) {
      $asset_ids[] = 0;
    }

    // Filter to only include assets with those IDs.
    $this->ensureMyTable();
    $this->query->addWhere('0', "$this->tableAlias.id", $asset_ids, 'IN');
  }

}

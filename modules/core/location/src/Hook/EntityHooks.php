<?php

declare(strict_types=1);

namespace Drupal\farm_location\Hook;

use Drupal\Component\Datetime\TimeInterface;
use Drupal\Core\Cache\CacheTagsInvalidatorInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_geo\Traits\WktTrait;
use Drupal\farm_location\AssetLocationInterface;
use Drupal\farm_location\LogLocationInterface;
use Drupal\log\Entity\LogInterface;

/**
 * Entity hook implementations for farm_location.
 */
class EntityHooks {

  use WktTrait;

  /**
   * The name of the log asset field.
   *
   * @var string
   */
  const LOG_FIELD_ASSET = 'asset';

  public function __construct(
    protected LogLocationInterface $logLocation,
    protected AssetLocationInterface $assetLocation,
    protected CacheTagsInvalidatorInterface $cacheTagsInvalidator,
    protected TimeInterface $time,
  ) {}

  /**
   * Implements hook_ENTITY_TYPE_presave().
   */
  #[Hook('log_presave')]
  public function logPresave(LogInterface $log) {

    // Populate the log geometry from the location geometry.
    $this->populateGeometryFromLocation($log);

    // Invalidate asset caches when assets are moved.
    $this->invalidateAssetCacheOnMovement($log);
  }

  /**
   * Implements hook_ENTITY_TYPE_delete().
   */
  #[Hook('log_delete')]
  public function logDelete(LogInterface $log) {
    $this->invalidateAssetCacheOnMovement($log);
  }

  /**
   * Populate a log's geometry based on its location.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The Log entity.
   */
  protected function populateGeometryFromLocation(LogInterface $log): void {

    // Load location assets referenced by the log.
    $assets = $this->getLocationAssets($log);

    // If the log does not reference any location assets, we will have nothing
    // to copy from, so do nothing.
    if (empty($assets)) {
      return;
    }

    // If this is a new log and it has a geometry, do nothing.
    if (empty($log->getOriginal()) && $this->logLocation->hasGeometry($log)) {
      return;
    }

    // If this is an update to an existing log, and the new geometry is not
    // empty, perform some checks to see if we should proceed or not. We always
    // want to proceed if the updated log's geometry is empty because this is
    // an indication that it was cleared manually by the user in order to
    // re-populate it.
    if (!empty($log->getOriginal()) && $this->logLocation->hasGeometry($log)) {

      // If the original log has a custom geometry, do nothing.
      if ($this->hasCustomGeometry($log->getOriginal())) {
        return;
      }

      // If the geometry has changed, do nothing.
      $old_geometry = $this->logLocation->getGeometry($log->getOriginal());
      $new_geometry = $this->logLocation->getGeometry($log);
      if ($old_geometry != $new_geometry) {
        return;
      }
    }

    // Get the combined location asset geometry.
    $wkt = $this->getCombinedAssetGeometry($assets);

    // If the WKT is not empty, set the log geometry.
    if (!empty($wkt)) {
      $this->logLocation->setGeometry($log, $wkt);
    }
  }

  /**
   * Check if a log has a custom geometry.
   *
   * This is determined by checking to see if the log's geometry matches that
   * of the location assets it references. If it does not, and it is not empty,
   * them we assume it has a custom geometry.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The Log entity.
   *
   * @return bool
   *   Returns TRUE if it matches, FALSE otherwise.
   */
  protected function hasCustomGeometry(LogInterface $log): bool {

    // If the log's geometry is empty, then it does not have a custom geometry.
    if (!$this->logLocation->hasGeometry($log)) {
      return FALSE;
    }

    // Load location assets referenced by the log.
    $assets = $this->getLocationAssets($log);

    // Get the combined location asset geometry.
    $location_geometry = $this->getCombinedAssetGeometry($assets);

    // Get the log geometry.
    $log_geometry = $this->logLocation->getGeometry($log);

    // Compare the log and location geometries.
    return $log_geometry != $location_geometry;
  }

  /**
   * Get location assets referenced by the log.
   *
   * This will first check for assets in the location reference field. If none
   * are found, it will also look for location assets in the asset reference
   * field.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The Log entity.
   *
   * @return \Drupal\asset\Entity\AssetInterface[]
   *   An array of location assets.
   */
  protected function getLocationAssets(LogInterface $log) {

    // Load location assets referenced by the log.
    $assets = $this->logLocation->getLocation($log);

    // If there are no assets in the location reference field, look for location
    // assets in the asset reference field. Only do this if the log is not a
    // movement, otherwise it would be impossible to clear the geometry of a
    // non-fixed location asset via movement Logs.
    if (empty($assets) && !$log->get('is_movement')->value) {
      foreach ($log->{static::LOG_FIELD_ASSET}->referencedEntities() as $asset) {
        if ($this->assetLocation->isLocation($asset)) {
          $assets[] = $asset;
        }
      }
    }

    return $assets;
  }

  /**
   * Load a combined set of location asset geometries.
   *
   * @param \Drupal\asset\Entity\AssetInterface[] $assets
   *   An array of location assets.
   *
   * @return string
   *   Returns a WKT string of the combined asset geometries.
   */
  protected function getCombinedAssetGeometry(array $assets): string {

    // Collect all the location geometries.
    $geoms = [];
    foreach ($assets as $asset) {
      if ($this->assetLocation->hasGeometry($asset)) {
        $geoms[] = $this->assetLocation->getGeometry($asset);
      }
    }

    // Combine the geometries into a single WKT string.
    $wkt = $this->combineWkt($geoms);

    return $wkt;
  }

  /**
   * Invalidate asset caches when assets are moved.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The Log entity.
   */
  protected function invalidateAssetCacheOnMovement(LogInterface $log): void {

    // Keep track if we need to invalidate the cache of referenced assets so
    // the computed 'location' and 'geometry' fields are updated.
    $update_asset_cache = FALSE;

    // If the log is a 'done' movement log, invalidate the cache.
    if ($this->isActiveMovementLog($log)) {
      $update_asset_cache = TRUE;
    }

    // If updating an existing 'done' movement log, invalidate the cache.
    // This catches any movement logs changing from done to another status.
    if (!empty($log->getOriginal()) && $this->isActiveMovementLog($log->getOriginal())) {
      $update_asset_cache = TRUE;
    }

    // If an update is not necessary, bail.
    if (!$update_asset_cache) {
      return;
    }

    // Build a list of cache tags.
    // @todo Only invalidate cache if the movement log changes the asset's current location. This might be different for each asset.
    $tags = [];

    // Include assets that were previously referenced.
    if (!empty($log->getOriginal())) {
      foreach ($log->getOriginal()->get('asset')->referencedEntities() as $asset) {
        array_push($tags, ...$asset->getCacheTags());
      }
    }

    // Include assets currently referenced by the log.
    foreach ($log->get('asset')->referencedEntities() as $asset) {
      array_push($tags, ...$asset->getCacheTags());
    }

    // Invalidate the cache tags.
    $this->cacheTagsInvalidator->invalidateTags($tags);
  }

  /**
   * Helper method to check if a log is an active movement log.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The Log entity.
   *
   * @return bool
   *   Boolean indicating if the log is an active movement log.
   */
  protected function isActiveMovementLog(LogInterface $log): bool {
    return $log->get('status')->value == 'done' && $log->get('is_movement')->value && $log->get('timestamp')->value <= $this->time->getCurrentTime();
  }

}

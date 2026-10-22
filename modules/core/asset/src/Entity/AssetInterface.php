<?php

declare(strict_types=1);

namespace Drupal\asset\Entity;

use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Entity\EntityChangedInterface;
use Drupal\Core\Entity\RevisionLogInterface;
use Drupal\user\EntityOwnerInterface;

/**
 * Provides an interface for defining asset entities.
 *
 * @ingroup asset
 */
interface AssetInterface extends ContentEntityInterface, EntityChangedInterface, RevisionLogInterface, EntityOwnerInterface {

  /**
   * Gets the asset name.
   *
   * @return string
   *   The asset name.
   */
  public function getName();

  /**
   * Sets the asset name.
   *
   * @param string $name
   *   The asset name.
   *
   * @return \Drupal\asset\Entity\AssetInterface
   *   The asset entity.
   */
  public function setName($name);

  /**
   * Gets the asset creation timestamp.
   *
   * @return int
   *   Creation timestamp of the asset.
   */
  public function getCreatedTime();

  /**
   * Sets the asset creation timestamp.
   *
   * @param int $timestamp
   *   Creation timestamp of the asset.
   *
   * @return \Drupal\asset\Entity\AssetInterface
   *   The asset entity.
   */
  public function setCreatedTime($timestamp);

  /**
   * Gets the asset archived timestamp.
   *
   * @return int|null
   *   Archived timestamp of the plan, or NULL if the asset has not been
   *   archived.
   *
   * @deprecated in farm:4.0.0 and is removed from farm:5.0.0.
   *   The last_archived field will be removed from assets and all data in it
   *   will be deleted in farmOS 5.x. Users are encouraged to decide if they
   *   need this information and migrate it to another place.
   * @see https://www.drupal.org/node/3539444
   */
  public function getArchivedTime();

  /**
   * Sets the asset archived timestamp.
   *
   * @param int|string|null $timestamp
   *   Archived timestamp of the asset.
   *
   * @return \Drupal\asset\Entity\AssetInterface
   *   The asset entity.
   *
   * @deprecated in farm:4.0.0 and is removed from farm:5.0.0.
   *   The last_archived field will be removed from assets and all data in it
   *   will be deleted in farmOS 5.x. Users are encouraged to decide if they
   *   need this information and migrate it to another place.
   * @see https://www.drupal.org/node/3539444
   */
  public function setArchivedTime($timestamp);

  /**
   * Gets the label of the asset type.
   *
   * @return string
   *   The label of the asset type.
   */
  public function getBundleLabel();

}

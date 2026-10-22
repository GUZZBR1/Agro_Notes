<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Annotation;

use Drupal\Component\Annotation\Plugin;

/**
 * Defines the quantity type plugin annotation object.
 *
 * Plugin namespace: Plugin\Quantity\QuantityType.
 *
 * @deprecated in farm:4.0.0 and is removed from farm:5.0.0.
 *   Use Attributes moving forward.
 * @see https://www.drupal.org/node/3523485
 * @see https://www.drupal.org/project/farm/issues/3461548
 *
 * @see plugin_api
 *
 * @Annotation
 */
class QuantityType extends Plugin {

  /**
   * The plugin ID.
   *
   * @var string
   */
  public $id;

  /**
   * The quantity type label.
   *
   * @var \Drupal\Core\Annotation\Translation
   *
   * @ingroup plugin_translatable
   */
  public $label;

}

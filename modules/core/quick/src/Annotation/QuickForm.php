<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Annotation;

use Drupal\Component\Annotation\Plugin;

/**
 * Defines a quick form annotation object.
 *
 * @deprecated in farm:4.0.0 and is removed from farm:5.0.0.
 *   Use Attributes moving forward.
 * @see https://www.drupal.org/node/3523485
 * @see https://www.drupal.org/project/farm/issues/3461548
 *
 * @Annotation
 */
class QuickForm extends Plugin {

  /**
   * The quick form ID.
   *
   * @var string
   */
  public $id;

  /**
   * The quick form label.
   *
   * @var \Drupal\Core\Annotation\Translation
   *
   * @ingroup plugin_translatable
   */
  public $label;

  /**
   * The quick form description.
   *
   * @var \Drupal\Core\Annotation\Translation
   *
   * @ingroup plugin_translatable
   */
  public $description;

  /**
   * The quick form help text.
   *
   * @var \Drupal\Core\Annotation\Translation
   *
   * @ingroup plugin_translatable
   */
  public $helpText;

  /**
   * An array of access permissions for the quick form.
   *
   * @var string[]
   */
  public $permissions;

  /**
   * Require a quick form instance entity to instantiate.
   *
   * @var bool
   */
  public $requiresEntity;

}
